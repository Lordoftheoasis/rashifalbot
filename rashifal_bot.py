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
    
    def get_sign_personality(self, sign_english):
        """Get personality traits for each sign"""
        personalities = {
            "Aries": "impulsive, competitive, always rushing, terrible at texting back, starts fights",
            "Taurus": "stubborn, food-obsessed, never changes their mind, slow to move on, materialistic",
            "Gemini": "two-faced, can't commit, texts everyone, gossips constantly, contradicts themselves",
            "Cancer": "clingy, emotional, holds grudges forever, plays victim, manipulates with tears",
            "Leo": "attention-seeking, dramatic, makes everything about them, needs constant validation",
            "Virgo": "critical, perfectionist, judges everyone, overthinks everything, passive-aggressive",
            "Libra": "indecisive, people-pleasing, avoids conflict, serial dater, fake nice",
            "Scorpio": "possessive, vengeful, stalks exes, intimidating, keeps secrets",
            "Sagittarius": "commitment-phobic, blunt, ghosting expert, can't sit still, brutal honesty",
            "Capricorn": "workaholic, emotionally unavailable, status-obsessed, cold, calculating",
            "Aquarius": "detached, emotionally distant, thinks they're special, rebel without a cause",
            "Pisces": "delusional, martyr complex, escapes reality, always the victim, overly sensitive"
        }
        return personalities.get(sign_english, "")
    
    def generate_rashifal(self, sign_info):
        """Generate rashifal for a sign"""
        
        # Get sign personality traits
        personality = self.get_sign_personality(sign_info['english'])
        
        # Pick random other sign for relational horoscopes
        other_signs = [s for s in self.zodiac_signs if s['english'] != sign_info['english']]
        other_sign = random.choice(other_signs)
        
        # Enhanced prompt with sign-specific personality and relational elements
        prompt = f"""Write ONE witty, slightly brutal horoscope for {sign_info['romanized']} ({sign_info['english']}).

{sign_info['english']} traits: {personality}

Write in one of these styles:
1. Direct callout: "{sign_info['romanized']}, stop pretending you're over it when you check their story every day."
2. Relational/comparative: "{sign_info['romanized']}, to {other_sign['romanized']} you are somewhere between a painful reminder and a terrible dream."
3. Brutally honest observation: "{sign_info['romanized']}, your standards aren't high, you just want someone who doesn't exist."

Be witty, sarcastic, brutally honest, and reference their actual zodiac personality traits.
Start ONLY with: {sign_info['romanized']}, [your witty message].

Write for {sign_info['romanized']}:"""
        
        try:
            completion = self.client.chat.completions.create(
                model="meta-llama/Llama-3.2-3B-Instruct",
                messages=[
                    {
                        "role": "system",
                        "content": "You write brutally honest, witty horoscopes that call people out. Be sarcastic and reference actual zodiac stereotypes. Keep it one sentence. No meta-commentary, no instructions, just the horoscope itself."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                max_tokens=100,
                temperature=0.9
            )
            
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
                        print(f"🎯 Raw generated: {raw_text}")
                        print(f"✨ Cleaned: {rashifal_text}")
                        return rashifal_text
            
            # If generation fails completely, raise error instead of using fallback
            raise Exception("Failed to generate valid horoscope")
            
        except Exception as e:
            print(f"❌ Generation error: {e}")
            raise
    
    def post_tweet(self, rashifal, sign_info):
        """Post rashifal to Twitter"""
        try:
            # Extract message
            message_part = rashifal
            if rashifal.startswith(sign_info['romanized']):
                message_part = rashifal[len(sign_info['romanized']):].lstrip(', ')
            
            message_part = self.clean_ai_text(message_part)
            
            # Capitalize first letter
            if message_part:
                message_part = message_part[0].upper() + message_part[1:]
            
            # Format tweet
            tweet_text = f"{sign_info['romanized']}, {message_part}"
            
            # Post
            if self.use_v1_api and self.twitter_api_v1:
                response = self.twitter_api_v1.update_status(tweet_text)
                tweet_id = response.id_str
            else:
                response = self.twitter_client.create_tweet(text=tweet_text)
                tweet_id = response.data['id']
            
            print(f"✅ Tweet posted successfully!")
            print(f"🐦 Tweet: {tweet_text}")
            print(f"🔗 Tweet ID: {tweet_id}")
            print(f"📊 Characters: {len(tweet_text)}/280")
            
            return True
            
        except Exception as e:
            print(f"❌ Tweet failed: {e}")
            return False

def main():
    """Main function to run the bot"""
    print(" Starting Rashifal Twitter Bot")
    print(f" {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 50)
    
    # Check environment variables
    print("\n🔐 Checking environment variables...")
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
            print(f"❌ {var}: NOT SET")
        else:
            # Show first/last 4 chars for verification
            masked = f"{value[:4]}...{value[-4:]}" if len(value) > 8 else "***"
            print(f"bhayo {var}: {masked}")
    
    if missing_vars:
        print(f"\n❌ Missing secrets: {', '.join(missing_vars)}")
        print("Please add these in GitHub Settings → Secrets and variables → Actions")
        return 1
    
    try:
        # Initialize bot
        print("\n🤖 Initializing bot...")
        bot = RashifalBot()
        
        # Pick random sign
        sign = random.choice(bot.zodiac_signs)
        print(f"\n🎯 Selected sign: {sign['romanized']} ({sign['english']})")
        
        # Generate rashifal
        print("🔄 Generating rashifal...")
        rashifal = bot.generate_rashifal(sign)
        print(f"✨ Generated: {rashifal}")
        
        # Post to Twitter
        print("\n📤 Posting to Twitter...")
        success = bot.post_tweet(rashifal, sign)
        
        if success:
            print("bhayo man!")
            return 0
        else:
            print("\n⚠️ check gara ta")
            return 1
            
    except Exception as e:
        print(f"\n bhayena: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    exit(main())
