
#!/usr/bin/env python3
"""
Rashifal Twitter Bot - Standalone version for GitHub Actions
Posts horoscope tweets with proper romanization
"""

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
                print(f"✅ Twitter API v2 connected as @{me.data.username}")
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
                print(f"✅ Twitter API v1.1 connected as @{user.screen_name}")
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
        
        # Simple, example-based prompt
        prompt = f"""Write one complete horoscope sentence for {sign_info['romanized']}.

Start directly with: {sign_info['romanized']}, [your message here].

Example format: Meṣa, your energy is shifting in beautiful ways.

Now write for {sign_info['romanized']}:"""
        
        try:
            completion = self.client.chat.completions.create(
                model="openai/gpt-oss-20b:nebius",
                messages=[
                    {
                        "role": "system",
                        "content": "You write horoscopes. Write only the horoscope sentence itself. Follow the exact format shown in the example. Do not add any rules, instructions, or meta-commentary."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                max_tokens=50,
                temperature=0.8
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
                            if len(rashifal_text.split()) > 15:
                                rashifal_text = None
                            else:
                                rashifal_text = rashifal_text.rstrip(',') + '.'
                    
                    if rashifal_text:
                        return rashifal_text
            
            # Fallback messages
            fallbacks = [
                f"{sign_info['romanized']}, stop overthinking and trust your instincts.",
                f"{sign_info['romanized']}, someone's been thinking about you more than you know.",
                f"{sign_info['romanized']}, your energy is magnetic today.",
                f"{sign_info['romanized']}, that person isn't worth your peace of mind.",
                f"{sign_info['romanized']}, your intuition has been trying to tell you something.",
                f"{sign_info['romanized']}, you're not responsible for other people's emotions.",
                f"{sign_info['romanized']}, trust the process, everything is falling into place.",
                f"{sign_info['romanized']}, you're stronger than you think.",
                f"{sign_info['romanized']}, stop apologizing for taking up space.",
                f"{sign_info['romanized']}, your standards aren't too high."
            ]
            return random.choice(fallbacks)
            
        except Exception as e:
            print(f"❌ Generation error: {e}")
            return f"{sign_info['romanized']}, trust your instincts today."
    
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
    print("🌟 Starting Rashifal Twitter Bot")
    print(f"📅 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 50)
    
    try:
        # Initialize bot
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
            print("\n✅ Bot completed successfully!")
            return 0
        else:
            print("\n⚠️ Bot completed with warnings")
            return 1
            
    except Exception as e:
        print(f"\n❌ Bot failed: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    exit(main())
