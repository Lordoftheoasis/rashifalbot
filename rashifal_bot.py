#!/usr/bin/env python3

import os
import random
import tweepy
import re
from datetime import datetime
from openai import OpenAI

class RashifalBot:
    def __init__(self):
        """Initialize bot with credentials from environment variables"""
        # HuggingFace API
        self.client = OpenAI(
            base_url="https://router.huggingface.co/v1",
            api_key=os.environ.get('HF_TOKEN'),
        )
        
        # Twitter credentials
        self.twitter_client = None
        self.twitter_api_v1 = None
        self.use_v1_api = False
        self.setup_twitter()
        
        # Zodiac signs with romanization
        self.zodiac_signs = [
            {"nepali": "मेष", "romanized": "Meṣa", "english": "Aries", "emoji": "♈"},
            {"nepali": "वृषभ", "romanized": "Vṛṣabha", "english": "Taurus", "emoji": "♉"},
            {"nepali": "मिथुन", "romanized": "Mithuna", "english": "Gemini", "emoji": "♊"},
            {"nepali": "कर्कट", "romanized": "Karkaṭa", "english": "Cancer", "emoji": "♋"},
            {"nepali": "सिंह", "romanized": "Siṃha", "english": "Leo", "emoji": "♌"},
            {"nepali": "कन्या", "romanized": "Kanyā", "english": "Virgo", "emoji": "♍"},
            {"nepali": "तुला", "romanized": "Tulā", "english": "Libra", "emoji": "♎"},
            {"nepali": "वृश्चिक", "romanized": "Vṛśchika", "english": "Scorpio", "emoji": "♏"},
            {"nepali": "धनु", "romanized": "Dhanu", "english": "Sagittarius", "emoji": "♐"},
            {"nepali": "मकर", "romanized": "Makara", "english": "Capricorn", "emoji": "♑"},
            {"nepali": "कुम्भ", "romanized": "Kumbha", "english": "Aquarius", "emoji": "♒"},
            {"nepali": "मीन", "romanized": "Mīna", "english": "Pisces", "emoji": "♓"}
        ]
        
        # Sign personality traits (updated with more nuance)
        self.personalities = {
            "Aries": "impulsive trailblazer, energetic and enthusiastic, drags people on adventures, makes hasty decisions, natural leader who thrives on challenges",
            "Taurus": "stubborn bull, loves comfort and luxury, incredibly reliable but resistant to change, appreciates good food and beauty",
            "Gemini": "social butterfly with the twins, quick-witted and charming, talks to everyone, versatile but inconsistent, indecisive",
            "Cancer": "emotional crab, deeply intuitive nurturer, connected to home and family, moody and sensitive, offers shoulder to cry on",
            "Leo": "confident lion, natural performer who loves spotlight, generous and warm-hearted protector, can seem arrogant, undeniably loyal",
            "Virgo": "precise virgin, analytical and detail-oriented, strives for perfection, overly critical but wants to help, meticulous attention to everything",
            "Libra": "diplomatic scales, sees both sides, values fairness and beauty, thrives in artistic environments, quest for balance leads to indecisiveness",
            "Scorpio": "intense scorpion, passionate and magnetic, deeply loyal but secretive, vengeful if crossed, transforms and rises from challenges",
            "Sagittarius": "philosophical archer, optimistic freedom-lover, seeks knowledge and experiences, straightforward honesty mistaken for tactlessness",
            "Capricorn": "ambitious goat, hardworking and disciplined, achieves success through perseverance, serious and stern, strong sense of responsibility",
            "Aquarius": "innovative water bearer, forward-thinking humanitarian, independent and values freedom, unconventional ideas seem eccentric, visionary",
            "Pisces": "dreamy fish, intuitive and compassionate, creative and imaginative, sensitive leading to escapism, boundless empathy and kindness"
        }
    
    def setup_twitter(self):
        """Setup Twitter API from environment variables"""
        try:
            # Try API v2 first
            self.twitter_client = tweepy.Client(
                bearer_token=os.environ.get('TWITTER_BEARER_TOKEN'),
                consumer_key=os.environ.get('TWITTER_CONSUMER_KEY'),
                consumer_secret=os.environ.get('TWITTER_CONSUMER_SECRET'),
                access_token=os.environ.get('TWITTER_ACCESS_TOKEN'),
                access_token_secret=os.environ.get('TWITTER_ACCESS_TOKEN_SECRET'),
                wait_on_rate_limit=True
            )
            
            try:
                me = self.twitter_client.get_me()
                print(f"dunn Twitter API v2 connected as @{me.data.username}")
                return
            except:
                print("⚠️ Twitter API v2 failed, trying v1.1...")
                
                # Fallback to API v1.1
                auth = tweepy.OAuth1UserHandler(
                    os.environ.get('TWITTER_CONSUMER_KEY'),
                    os.environ.get('TWITTER_CONSUMER_SECRET'),
                    os.environ.get('TWITTER_ACCESS_TOKEN'),
                    os.environ.get('TWITTER_ACCESS_TOKEN_SECRET')
                )
                self.twitter_api_v1 = tweepy.API(auth, wait_on_rate_limit=True)
                user = self.twitter_api_v1.verify_credentials()
                print(f"dunn Twitter API v1.1 connected as @{user.screen_name}")
                self.use_v1_api = True
                
        except Exception as e:
            print(f"❌ Twitter setup failed: {e}")
            raise
    
    def clean_ai_text(self, text):
        """Remove AI giveaways"""
        text = text.replace('—', ',').replace('–', ',')
        
        # Remove instruction lines
        lines = text.split('\n')
        cleaned_lines = []
        for line in lines:
            line = line.strip()
            if any(keyword in line.lower() for keyword in [
                'must be', 'should be', 'critical', 'mandatory', 'required',
                'strict', 'rule', 'format:', 'example:', 'write for',
                'now write', 'the horoscope:', 'message:', 'advice:'
            ]):
                continue
            if line:
                cleaned_lines.append(line)
        
        if cleaned_lines:
            text = cleaned_lines[0]
        
        # Remove meta-commentary
        meta_patterns = [
            r'^(A sentence like|Something like|Could be|For example|Like this|Try this|How about):\s*',
            r'^(So|Could be|For example|Like this|Something like)\b[,:]?\s*',
            r'^-\s*',
        ]
        
        for pattern in meta_patterns:
            text = re.sub(pattern, '', text, flags=re.IGNORECASE)
        
        text = re.sub(r'"([^"]*)"', r'\1', text)
        
        ai_phrases = [
            'as an AI', 'I cannot', 'I apologize', 'I understand',
            'must be a complete sentence', 'ending properly'
        ]
        
        for phrase in ai_phrases:
            text = text.replace(phrase, '').replace(phrase.capitalize(), '')
        
        text = ' '.join(text.split())
        text = text.strip(' .,;:-')
        
        return text
    
    def generate_rashifal(self, sign_info):
        """Generate rashifal for a sign"""
        
        # Get sign personality traits
        personality = self.personalities[sign_info['english']]
        
        # Pick random other sign for relational horoscopes
        other_signs = [s for s in self.zodiac_signs if s['english'] != sign_info['english']]
        other_sign = random.choice(other_signs)
        
        # Randomly choose positive or negative tone (10% positive, 90% negative)
        tone = "positive" if random.random() < 0.1 else "negative"
        
        if tone == "positive":
            prompt = f"""Write ONE witty, slightly uplifting horoscope for {sign_info['romanized']} ({sign_info['english']}).

{sign_info['english']} traits: {personality}

Examples:
- "{sign_info['romanized']}, your overthinking is finally paying off."
- "{sign_info['romanized']}, someone finally appreciates your intensity."
- "Your instincts were right all along, {sign_info['romanized']}."

Keep it natural length (10-20 words). Be encouraging but still witty.

CRITICAL: If mentioning another sign, use ONLY romanized names:
Meṣa, Vṛṣabha, Mithuna, Karkaṭa, Siṃha, Kanyā, Tulā, Vṛśchika, Dhanu, Makara, Kumbha, Mīna

Start with: {sign_info['romanized']}, [your message].

Write for {sign_info['romanized']}:"""
        else:
            prompt = f"""Write ONE witty, snarky, brutally honest horoscope for {sign_info['romanized']} ({sign_info['english']}).

{sign_info['english']} traits: {personality}

Examples of SNARKY, MEAN style:
{sign_info['romanized']}, pretending you don’t care is getting exhausting; isn’t it?
Love isn’t dead, {sign_info['romanized']}; it’s just ignoring your texts.
You weren’t ghosted, {sign_info['romanized']}; you were spiritually redirected.
{sign_info['romanized']}, stop calling it a ‘situationship’; it’s a warning sign.
You wanted closure, {sign_info['romanized']}; but you really wanted control.
They didn’t change, {sign_info['romanized']}; you just stopped making excuses.
If it feels like deja vu, {sign_info['romanized']}; that’s just your bad decisions looping.
{sign_info['romanized']}, maybe it’s time to let go; of them and the playlist.
{sign_info['romanized']}, healing isn’t an aesthetic.
You call it intuition, {sign_info['romanized']}; everyone else calls it paranoia.
You’re not ‘over it,’ {sign_info['romanized']}; you’re just emotionally numb.
Your peace is fragile, {sign_info['romanized']}; handle with caffeine.
You’re not mysterious, {sign_info['romanized']}; you’re just emotionally unavailable.
{sign_info['romanized']}, you keep saying ‘it’s fine’ like it ever was.
The universe isn’t testing you, {sign_info['romanized']}; you just refuse to learn.
{sign_info['romanized']}, stop calling self-sabotage ‘a vibe.’
{sign_info['romanized']}, you don’t need a sign; you need therapy and better taste.
You can’t manifest accountability, {sign_info['romanized']}.
{sign_info['romanized']}, that ‘new chapter’ you’re starting looks suspiciously like a rerun.
The stars say rest; your bank account says grind, {sign_info['romanized']}.
Mercury isn’t in retrograde, {sign_info['romanized']}; you just made bad choices.
You said ‘new era’ but kept the same habits, {sign_info['romanized']}.
The energy’s off because you are, {sign_info['romanized']}.
{sign_info['romanized']}, your coping mechanisms deserve a performance review.
You’re not unlucky, {sign_info['romanized']}; you’re just consistent in chaos.
{sign_info['romanized']}, take a break from pretending you’re okay; you’ve earned it.
The stars are tired of warning you, {sign_info['romanized']}.
{sign_info['romanized']}, the universe is subtweeting you again.
{sign_info['romanized']}, stop overthinking; no one’s plotting against you, they’re just busy.
{sign_info['romanized']}, not everyone who smiles at you likes you; this isn’t Kathmandu traffic.
{sign_info['romanized']}, stop refreshing their story; Wi-Fi pani thakcha.
{sign_info['romanized']}, love isn’t astrology-proof; even if you blame Saturn every time.
You said you’re focusing on yourself, {sign_info['romanized']}; but you’re still online at 2 a.m.
{sign_info['romanized']}, maybe stop texting your ex every time it rains.
{sign_info['romanized']}, calling it ‘main character energy’ doesn’t make the chaos cinematic.
{sign_info['romanized']}, you’re not manifesting; you’re just procrastinating with incense.
{sign_info['romanized']}, not everything is a cosmic sign; some things are just bad life choices.
{sign_info['romanized']}, your toxic trait is thinking everyone’s your soulmate after one tea break.
{sign_info['romanized']}, stop expecting closure from people who can’t even reply ‘ok’.
{sign_info['romanized']}, they didn’t ghost you; it’s just load-shedding of emotions.
You can’t vibe your way out of consequences, {sign_info['romanized']}.
{sign_info['romanized']}, if they cared, they’d reply before the next load-shedding schedule.
The universe isn’t sending mixed signals, {sign_info['romanized']}; that’s just you refreshing messages again.
{sign_info['romanized']}, stop saying it’s the planets; it’s just poor decision-making in HD.
You don’t need the stars, {sign_info['romanized']}; you need sleep and a data pack.
{sign_info['romanized']}, you can’t heal in Thamel and call it self-discovery.
{sign_info['romanized']}, your karmic debt looks like an eSewa balance right now; zero.
{sign_info['romanized']}, you keep chasing people like microbuses chase passengers; desperate and loud.
{sign_info['romanized']}, don’t blame Mercury; blame that 2 a.m. call to your ex.
{sign_info['romanized']}, you say you’re manifesting peace but still arguing in group chats.
{sign_info['romanized']}, your heart’s been broken so often it needs a Sajha bus schedule.
{sign_info['romanized']}, stop posting “new beginnings”; you said that last Dashain too.
{sign_info['romanized']}, not everything is deep; some of it is just poor Wi-Fi and worse timing.
{sign_info['romanized']}, the planets aren’t against you; you’re just late again.
{sign_info['romanized']}, stop calling it healing; you’re just in Pokhara again.
{sign_info['romanized']}, your aura looks like traffic near Kalanki right now.
{sign_info['romanized']}, stop flirting like you’re bargaining at Asan.
{sign_info['romanized']}, maybe meditate; or at least uninstall Instagram for a week.
{sign_info['romanized']}, your “new mindset” still complains about horoscope posts.
{sign_info['romanized']}, not every vibe check is cosmic; some are just karma catching up.
{sign_info['romanized']}, you don’t need a tarot reading; you need to log off and touch some hills
Be MEAN, SNARKY, call them out. Reference zodiac traits. Natural length (15-30 words).

CRITICAL: If mentioning another sign, use ONLY romanized names, do not repeat the same sign names twice

Start with: {sign_info['romanized']}, [your snarky message].

Write for {sign_info['romanized']}:"""
        
        max_retries = 3
        retry_count = 0
        
        while retry_count < max_retries:
            try:
                completion = self.client.chat.completions.create(
                    model="meta-llama/Llama-3.2-3B-Instruct",
                    messages=[
                        {
                            "role": "system",
                            "content": f"You write {'slightly uplifting' if tone == 'positive' else 'brutally honest, mean, snarky'} horoscopes. Be witty and {'encouraging' if tone == 'positive' else 'call people out on their BS'}. Natural length, not too short or long."
                        },
                        {
                            "role": "user",
                            "content": prompt
                        }
                    ],
                    max_tokens=80,
                    temperature=0.9
                )
                
                # If we got here, API call succeeded
                break
                
            except Exception as api_error:
                retry_count += 1
                if "rate limit" in str(api_error).lower():
                    if retry_count < max_retries:
                        print(f" Rate limit hit, attempt {retry_count}/{max_retries}")
                        print(f"   Waiting 60 seconds before retry...")
                        import time
                        time.sleep(60)
                    else:
                        print(f" Rate limit exceeded after {max_retries} attempts")
                        raise Exception("Rate limit exceeded, cannot generate horoscope")
                else:
                    raise api_error
        
        try:
            if completion and completion.choices:
                message = completion.choices[0].message
                
                if message and hasattr(message, 'content') and message.content:
                    raw_text = message.content.strip()
                    
                    # Check for meta-commentary
                    if re.match(r'^(A sentence like|Something like|Could be|For example|Like this|Try this|How about):', raw_text, re.IGNORECASE):
                        match = re.search(r'[:"]\s*(.+?)[".]?\s*$', raw_text)
                        rashifal_text = match.group(1).strip() if match else None
                    else:
                        rashifal_text = raw_text
                    
                    if rashifal_text:
                        rashifal_text = self.clean_ai_text(rashifal_text)
                        
                        # Add period if missing
                        if rashifal_text and not rashifal_text.endswith(('.', '!', '?')):
                            rashifal_text = rashifal_text.rstrip(',') + '.'
                    
                    if rashifal_text:
                        print(f" Raw generated: {raw_text}")
                        print(f" Cleaned: {rashifal_text}")
                        print(f" Tone: {tone}")
                        return rashifal_text
            
            # If generation fails completely, raise error
            raise Exception("Failed to generate valid horoscope")
            
        except Exception as e:
            print(f" Generation error: {e}")
            raise
    
    def post_tweet(self, rashifal, sign_info):
        """Post rashifal to Twitter"""
        try:
            # Clean the generated text
            rashifal = self.clean_ai_text(rashifal)
            
            # If it already starts with the sign name, use it as is
            if rashifal.startswith(sign_info['romanized']):
                tweet_text = rashifal
            else:
                # Otherwise, add the sign name at the beginning
                # Capitalize first letter of message
                if rashifal:
                    rashifal = rashifal[0].upper() + rashifal[1:]
                tweet_text = f"{sign_info['romanized']}, {rashifal}"
            
            # Post
            if self.use_v1_api and self.twitter_api_v1:
                response = self.twitter_api_v1.update_status(tweet_text)
                tweet_id = response.id_str
            else:
                response = self.twitter_client.create_tweet(text=tweet_text)
                tweet_id = response.data['id']
            
            print(f" Tweet posted successfully!")
            print(f" Tweet: {tweet_text}")
            print(f" Tweet ID: {tweet_id}")
            print(f" Characters: {len(tweet_text)}/280")
            
            return True
            
        except Exception as e:
            print(f" Tweet failed: {e}")
            return False

def main():
    """Main function to run the bot"""
    print(" Starting Rashifal Twitter Bot")
    print(f" {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 50)
    
    # Check environment variables
    print("\n Checking environment variables...")
    required_vars = [
        'HF_TOKEN',
        'TWITTER_CONSUMER_KEY',
        'TWITTER_CONSUMER_SECRET',
        'TWITTER_ACCESS_TOKEN',
        'TWITTER_ACCESS_TOKEN_SECRET',
        'TWITTER_BEARER_TOKEN'
    ]
    
    missing_vars = []
    for var in required_vars:
        value = os.environ.get(var)
        if not value:
            missing_vars.append(var)
            print(f" {var}: NOT SET")
        else:
            # Show first/last 4 chars for verification
            masked = f"{value[:4]}...{value[-4:]}" if len(value) > 8 else "***"
            print(f"bhayo {var}: {masked}")
    
    if missing_vars:
        print(f"\n Missing secrets: {', '.join(missing_vars)}")
        print("Please add these in GitHub Settings → Secrets and variables → Actions")
        return 1
    
    try:
        # Initialize bot
        print("\n🤖 Initializing bot...")
        bot = RashifalBot()
        
        # Pick random sign
        sign = random.choice(bot.zodiac_signs)
        print(f"\n Selected sign: {sign['romanized']} ({sign['english']})")
        
        # Generate rashifal
        print(" Generating rashifal...")
        rashifal = bot.generate_rashifal(sign)
        print(f" Generated: {rashifal}")
        
        # Post to Twitter
        print("\n📤 Posting to Twitter...")
        success = bot.post_tweet(rashifal, sign)
        
        if success:
            print("bhayo man!")
            return 0
        else:
            print("\n check gara ta")
            return 1
            
    except Exception as e:
        print(f"\n bhayena: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    exit(main())
