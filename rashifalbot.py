#!/usr/bin/env python3

import os
import random
import re
import time
import logging
from datetime import datetime
import tweepy
from groq import Groq

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

ZODIAC_SIGNS = [
    "Mesa", "Vrishabha", "Mithuna", "Karkata", "Simha", "Kanya",
    "Tula", "Vrischika", "Dhanu", "Makara", "Kumbha", "Mina",
]

NEGATIVE_EXAMPLES = [
    "pretending you don't care is getting exhausting, isn't it?",
    "love isn't dead; it's just ignoring your texts.",
    "You weren't ghosted; you were spiritually redirected.",
    "stop calling it a 'situationship'; they just don't like you that much.",
    "they didn't change; you just stopped making excuses.",
    "healing isn't an aesthetic.",
    "you call it intuition, everyone else calls it paranoia.",
    "your peace is fragile; handle with caffeine.",
    "stop calling self-sabotage 'a vibe.'",
    "the universe isn't testing you; you just refuse to learn.",
    "Mercury isn't in retrograde; you just made bad choices.",
    "the energy's off because you are.",
    "maybe stop texting your ex every time you feel low.",
    "you're not manifesting; you're just procrastinating.",
    "You can't vibe your way out of consequences.",
    "your karmic debt looks like your bank balance right now.",
    "don't blame Mercury; blame that 2 a.m. call to your ex.",
    "your aura looks looks like tangled up wired earphones  right now.",
    
]

POSITIVE_EXAMPLES = [
    "your overthinking is finally paying off.",
    "someone finally appreciates your intensity.",
    "Your instincts were right all along.",
]


def get_env(key):
    val = os.environ.get(key)
    if not val:
        raise ValueError(f"Missing environment variable: {key}")
    return val


def clean_text(text):
    """Remove AI artifacts and meta-commentary."""
    text = text.replace('—', ',').replace('–', ',')
    text = re.sub(r'\s+-\s+', ', ', text)
    text = re.sub(r',?\s*as a \w+,?\s*', ' ', text, flags=re.IGNORECASE)
    text = re.sub(r'^(A sentence like|Something like|Could be|For example|Like this|Try this|How about):\s*', '', text, flags=re.IGNORECASE)
    text = re.sub(r'^(So|Could be|For example|Like this|Something like)\b[,:]?\s*', '', text, flags=re.IGNORECASE)
    text = re.sub(r'^-\s*', '', text)
    text = re.sub(r'"([^"]*)"', r'\1', text)

    skip_keywords = {'must be', 'should be', 'critical', 'mandatory', 'required',
                     'strict', 'rule', 'format:', 'example:', 'write for',
                     'now write', 'the horoscope:', 'message:', 'advice:'}
    lines = [l.strip() for l in text.split('\n') if l.strip()
             and not any(kw in l.lower() for kw in skip_keywords)]
    text = lines[0] if lines else ''

    text = ' '.join(text.split()).strip(' .,;:-')
    return text


def build_prompt(sign, tone):
    if tone == "positive":
        examples = '\n'.join(f'- "{sign}, {e}"' for e in random.sample(POSITIVE_EXAMPLES, 3))
        return (
            f"Write ONE witty, slightly uplifting horoscope for {sign}.\n\n"
            f"Examples:\n{examples}\n\n"
            f"Keep it 10-20 words. Be encouraging but witty.\n"
            f"Do NOT repeat the sign name twice.\n"
            f"Write for {sign}:"
        )
    else:
        examples = '\n'.join(f'- "{sign}, {e}"' for e in random.sample(NEGATIVE_EXAMPLES, 6))
        return (
            f"Write ONE witty, snarky, brutally honest horoscope for {sign}.\n\n"
            f"Examples:\n{examples}\n\n"
            f"Be MEAN and SNARKY. Keep it 15-30 words.\n"
            f"Do NOT repeat the sign name twice.\n"
            f"Write for {sign}:"
        )


def generate_rashifal(groq_client, model, sign, max_retries=3):
    tone = "positive" if random.random() < 0.1 else "negative"
    prompt = build_prompt(sign, tone)
    system = f"You write {'uplifting' if tone == 'positive' else 'brutally honest, snarky'} horoscopes."

    for attempt in range(1, max_retries + 1):
        try:
            completion = groq_client.chat.completions.create(
                model=model,
                messages=[{"role": "system", "content": system},
                          {"role": "user", "content": prompt}],
                max_tokens=80,
                temperature=0.9,
            )
            raw = completion.choices[0].message.content.strip()
            logger.info(f"Groq attempt {attempt} succeeded. Raw: {raw}")

            # Strip meta-commentary wrapper if present
            match = re.match(r'^(A sentence like|Something like|Could be|For example)[^:]*:\s*(.+)', raw, re.IGNORECASE)
            text = clean_text(match.group(2) if match else raw)

            if not text:
                raise ValueError("Empty text after cleaning")
            if not text.endswith(('.', '!', '?')):
                text = text.rstrip(',') + '.'

            logger.info(f"Cleaned: {text} | Tone: {tone}")
            return text

        except Exception as e:
            err = str(e).lower()
            if any(x in err for x in ["rate", "429", "limit", "too many"]) and attempt < max_retries:
                wait = 60 * attempt
                logger.warning(f"Rate limit, retrying in {wait}s...")
                time.sleep(wait)
            else:
                raise


def format_tweet(text, sign):
    text = clean_text(text)
    if not text.startswith(sign):
        text = f"{sign}, {text[0].upper() + text[1:]}"
    return text[:277] + "..." if len(text) > 280 else text


def post_tweet(twitter_client, twitter_v1, use_v1, tweet_text, max_retries=3):
    for attempt in range(1, max_retries + 1):
        try:
            if use_v1 and twitter_v1:
                resp = twitter_v1.update_status(tweet_text)
                tweet_id = resp.id_str
            else:
                resp = twitter_client.create_tweet(text=tweet_text)
                tweet_id = resp.data['id']
            logger.info(f"Posted: {tweet_text} | ID: {tweet_id} | {len(tweet_text)}/280 chars")
            return True

        except tweepy.errors.Forbidden as e:
            logger.error(f"Forbidden (check app permissions): {e}")
            return False
        except tweepy.errors.TooManyRequests:
            if attempt < max_retries:
                wait = 30 * attempt
                logger.warning(f"Twitter rate limit, retrying in {wait}s...")
                time.sleep(wait)
            else:
                logger.error("Twitter rate limit exceeded after all retries")
                return False
        except Exception as e:
            if attempt < max_retries:
                time.sleep(30 * attempt)
            else:
                logger.error(f"Tweet failed: {e}")
                return False


def setup_twitter():
    consumer_key    = get_env('TWITTER_CONSUMER_KEY')
    consumer_secret = get_env('TWITTER_CONSUMER_SECRET')
    access_token    = get_env('TWITTER_ACCESS_TOKEN')
    access_secret   = get_env('TWITTER_ACCESS_TOKEN_SECRET')
    bearer_token    = os.environ.get('TWITTER_BEARER_TOKEN')

    client = tweepy.Client(
        bearer_token=bearer_token,
        consumer_key=consumer_key,
        consumer_secret=consumer_secret,
        access_token=access_token,
        access_token_secret=access_secret,
        wait_on_rate_limit=True,
    )

    try:
        me = client.get_me()
        logger.info(f"Twitter v2 connected as @{me.data.username}")
        return client, None, False
    except Exception:
        logger.warning("Twitter v2 failed, falling back to v1.1...")
        auth = tweepy.OAuth1UserHandler(consumer_key, consumer_secret, access_token, access_secret)
        api_v1 = tweepy.API(auth, wait_on_rate_limit=True)
        user = api_v1.verify_credentials()
        logger.info(f"Twitter v1.1 connected as @{user.screen_name}")
        return client, api_v1, True


def main():
    logger.info(f"Starting Rashifal Bot — {datetime.now():%Y-%m-%d %H:%M:%S}")

    groq_client = Groq(api_key=get_env('GROQ_KEY'))
    model = os.environ.get('GROQ_MODEL', 'llama-3.3-70b-versatile')
    twitter_client, twitter_v1, use_v1 = setup_twitter()

    sign = random.choice(ZODIAC_SIGNS)
    logger.info(f"Sign: {sign}")

    rashifal = generate_rashifal(groq_client, model, sign)
    tweet_text = format_tweet(rashifal, sign)

    success = post_tweet(twitter_client, twitter_v1, use_v1, tweet_text)
    logger.info("SUCCESS" if success else "FAILED")
    return 0 if success else 1


if __name__ == "__main__":
    exit(main())