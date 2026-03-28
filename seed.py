import asyncio
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from datetime import datetime
from pathlib import Path
from motor.motor_asyncio import AsyncIOMotorClient
from config import get_settings
from utils.thumbnail_service import generate_thumbnail
from utils.template_storage import save_template, compute_content_hash, supports_image_feature

settings = get_settings()


MODERN_MINIMAL_HTML = '''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Wedding Invitation</title>
    <link href="https://fonts.googleapis.com/css2?family=Playfair+Display:wght@400;500;600;700&family=Inter:wght@300;400;500;600&display=swap" rel="stylesheet">
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: 'Inter', sans-serif;
            background: linear-gradient(135deg, #131313 0%, #1c1b1b 100%);
            min-height: 100vh;
            display: flex;
            align-items: center;
            justify-content: center;
            padding: 20px;
        }
        .invitation-card {
            background: #1c1b1b;
            max-width: 600px;
            width: 100%;
            padding: 60px 40px;
            border-radius: 10px;
            box-shadow: 0 20px 60px rgba(0, 0, 0, 0.5);
            text-align: center;
            border: 1px solid #2a2a2a;
        }
        .decorative-border { border: 2px solid #ffb784; padding: 40px; border-radius: 5px; }
        .wedding-title { font-size: 16px; letter-spacing: 3px; color: #ffb784; text-transform: uppercase; margin-bottom: 20px; font-weight: normal; }
        .couple-names { font-family: 'Playfair Display', serif; font-size: 48px; color: #e5e2e1; margin: 20px 0; font-weight: normal; line-height: 1.2; }
        .ampersand { font-size: 36px; color: #ffb784; margin: 0 10px; font-style: italic; }
        .family-names { font-size: 14px; color: #ccc9c8; margin: 25px 0; line-height: 1.8; }
        .divider { width: 80px; height: 2px; background: linear-gradient(to right, transparent, #ffb784, transparent); margin: 30px auto; }
        .event-details { margin: 30px 0; }
        .date { font-family: 'Playfair Display', serif; font-size: 24px; color: #bac3ff; margin-bottom: 10px; }
        .time { font-size: 18px; color: #9e9b9a; margin-bottom: 20px; }
        .venue { font-size: 16px; color: #e5e2e1; line-height: 1.6; font-style: italic; }
        .message { margin-top: 30px; font-size: 14px; color: #9e9b9a; line-height: 1.8; font-style: italic; }
        .image-container { margin: 30px auto; width: 150px; height: 150px; border-radius: 50%; overflow: hidden; border: 3px solid #bac3ff; display: none; }
        .image-container.visible { display: block; }
        .image-container img { width: 100%; height: 100%; object-fit: cover; }
        .ornament { font-size: 30px; color: #ffb784; margin: 20px 0; }
    </style>
</head>
<body>
    <div class="invitation-card">
        <div class="decorative-border">
            <div class="ornament">&#x2726;</div>
            <h2 class="wedding-title">Wedding Invitation</h2>
            <div class="couple-names">{{person2Name}}<span class="ampersand">&</span>{{person1Name}}</div>
            <div class="family-names">{{person2Family}}<br>&<br>{{person1Family}}</div>
            <div class="divider"></div>
            <div class="image-container"><img src="{{imageUrl}}" alt="Wedding" /></div>
            <div class="event-details">
                <div class="date">{{eventDate}}</div>
                <div class="time">{{eventTime}}</div>
                <div class="venue">{{venue}}</div>
            </div>
            <div class="divider"></div>
            <div class="message">{{message}}</div>
            <div class="ornament">&#x2726;</div>
        </div>
    </div>
</body>
</html>'''


ELEGANT_FLORAL_HTML = '''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Wedding Invitation</title>
    <link href="https://fonts.googleapis.com/css2?family=Cormorant+Garamond:wght@300;400;500;600;700&family=Montserrat:wght@300;400;500;600&family=Great+Vibes&display=swap" rel="stylesheet">
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { font-family: 'Montserrat', sans-serif; background: linear-gradient(135deg, #fdf6f0 0%, #f8e8e0 100%); min-height: 100vh; display: flex; justify-content: center; align-items: center; padding: 20px; }
        .invitation-card { background: linear-gradient(145deg, #ffffff 0%, #fef9f6 100%); max-width: 600px; width: 100%; padding: 60px 40px; border-radius: 8px; box-shadow: 0 25px 60px rgba(0, 0, 0, 0.1); position: relative; overflow: hidden; }
        .invitation-card::before { content: ''; position: absolute; top: 0; left: 0; right: 0; height: 6px; background: linear-gradient(90deg, #d4a574, #c9956c, #d4a574); }
        .ornament { text-align: center; margin-bottom: 30px; font-size: 40px; color: #d4a574; }
        .invite-text { font-family: 'Cormorant Garamond', serif; font-size: 16px; font-weight: 500; letter-spacing: 6px; text-transform: uppercase; color: #8b7355; margin-bottom: 20px; text-align: center; }
        .couple-names { text-align: center; margin-bottom: 30px; }
        .ampersand { font-family: 'Great Vibes', cursive; font-size: 48px; color: #d4a574; margin: 10px 0; }
        .name { font-family: 'Cormorant Garamond', serif; font-size: 42px; font-weight: 600; color: #2c2c2c; letter-spacing: 2px; }
        .family-text { font-family: 'Cormorant Garamond', serif; font-size: 16px; color: #6b6b6b; margin-top: 15px; font-style: italic; }
        .divider { display: flex; align-items: center; justify-content: center; margin: 35px 0; }
        .divider-line { width: 80px; height: 1px; background: #d4a574; }
        .divider-diamond { width: 10px; height: 10px; background: #d4a574; transform: rotate(45deg); margin: 0 15px; }
        .details { text-align: center; margin-bottom: 40px; }
        .detail-item { margin-bottom: 25px; }
        .detail-label { font-size: 12px; font-weight: 600; letter-spacing: 4px; text-transform: uppercase; color: #d4a574; margin-bottom: 8px; }
        .detail-value { font-family: 'Cormorant Garamond', serif; font-size: 24px; font-weight: 500; color: #2c2c2c; }
        .detail-sub { font-size: 14px; color: #6b6b6b; margin-top: 5px; }
        .message { background: #fdf9f7; padding: 25px; border-radius: 4px; margin-bottom: 30px; border-left: 3px solid #d4a574; }
        .message p { font-family: 'Cormorant Garamond', serif; font-size: 18px; font-style: italic; color: #555; line-height: 1.8; text-align: center; }
        .rsvp { text-align: center; padding-top: 20px; border-top: 1px solid #eee; }
        .rsvp-text { font-size: 14px; color: #888; margin-bottom: 15px; }
        .rsvp-contact { font-family: 'Cormorant Garamond', serif; font-size: 18px; color: #d4a574; }
        .couple-image { width: 150px; height: 150px; border-radius: 50%; object-fit: cover; display: none; margin: 0 auto 30px; border: 4px solid #f0e6dc; }
        .couple-image.visible { display: block; }
    </style>
</head>
<body>
    <div class="invitation-card">
        <img src="{{imageUrl}}" alt="Couple" class="couple-image">
        <div class="ornament">❦</div>
        <p class="invite-text">Wedding Invitation</p>
        <div class="couple-names">
            <span class="name">{{person1Name}}</span>
            <div class="ampersand">&</div>
            <span class="name">{{person2Name}}</span>
            <p class="family-text">{{person1Family}} & {{person2Family}}</p>
        </div>
        <div class="divider"><span class="divider-line"></span><span class="divider-diamond"></span><span class="divider-line"></span></div>
        <div class="details">
            <div class="detail-item"><p class="detail-label">When</p><p class="detail-value">{{eventDate}}</p><p class="detail-sub">{{eventTime}}</p></div>
            <div class="detail-item"><p class="detail-label">Where</p><p class="detail-value">{{venue}}</p></div>
        </div>
        <div class="message"><p>{{message}}</p></div>
        <div class="rsvp"><p class="rsvp-text">We would be honored by your presence</p><p class="rsvp-contact">Kindly RSVP</p></div>
    </div>
</body>
</html>'''


LUXURY_DARK_HTML = '''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Wedding Invitation</title>
    <link href="https://fonts.googleapis.com/css2?family=Playfair+Display:wght@400;500;600;700&family=Lato:wght@300;400;700&display=swap" rel="stylesheet">
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { font-family: 'Lato', sans-serif; background: linear-gradient(180deg, #1a1a2e 0%, #16213e 50%, #1a1a2e 100%); min-height: 100vh; display: flex; justify-content: center; align-items: center; padding: 20px; }
        .invitation-card { background: linear-gradient(135deg, #1f2937 0%, #111827 100%); max-width: 500px; width: 100%; padding: 50px 35px; border-radius: 4px; box-shadow: 0 30px 80px rgba(0, 0, 0, 0.5); border: 1px solid rgba(255, 215, 0, 0.1); position: relative; }
        .gold-border { position: absolute; top: 10px; left: 10px; right: 10px; bottom: 10px; border: 1px solid rgba(212, 175, 55, 0.3); border-radius: 2px; pointer-events: none; }
        .floral-top { text-align: center; font-size: 32px; color: #d4af37; margin-bottom: 25px; opacity: 0.8; }
        .subtitle { text-align: center; font-size: 11px; letter-spacing: 8px; text-transform: uppercase; color: #d4af37; margin-bottom: 20px; }
        .couple-names { text-align: center; margin: 30px 0; }
        .names { font-family: 'Playfair Display', serif; font-size: 38px; color: #ffffff; line-height: 1.3; }
        .ampersand { font-family: 'Great Vibes', cursive; font-size: 42px; color: #d4af37; display: block; margin: 5px 0; }
        .families { font-family: 'Lato', sans-serif; font-size: 12px; color: #9ca3af; margin-top: 15px; letter-spacing: 1px; }
        .gold-divider { width: 100px; height: 1px; background: linear-gradient(90deg, transparent, #d4af37, transparent); margin: 30px auto; }
        .details-box { background: rgba(255, 215, 0, 0.05); border: 1px solid rgba(212, 175, 55, 0.2); padding: 25px; margin: 25px 0; text-align: center; }
        .detail-row { margin: 15px 0; }
        .detail-label { font-size: 10px; letter-spacing: 3px; text-transform: uppercase; color: #d4af37; margin-bottom: 5px; }
        .detail-value { font-family: 'Playfair Display', serif; font-size: 20px; color: #ffffff; }
        .detail-sub { font-size: 13px; color: #9ca3af; }
        .message { font-family: 'Playfair Display', serif; font-size: 15px; color: #d4af37; font-style: italic; line-height: 1.8; text-align: center; margin: 25px 0; }
        .floral-bottom { text-align: center; font-size: 24px; color: #d4af37; opacity: 0.6; }
        .couple-image { width: 120px; height: 120px; border-radius: 50%; object-fit: cover; display: none; margin: 0 auto 25px; border: 3px solid rgba(212, 175, 55, 0.3); }
        .couple-image.visible { display: block; }
    </style>
</head>
<body>
    <div class="invitation-card">
        <div class="gold-border"></div>
        <div class="floral-top">❋</div>
        <p class="subtitle">The honor of your presence is requested</p>
        <img src="{{imageUrl}}" alt="Couple" class="couple-image">
        <div class="couple-names">
            <span class="names">{{person1Name}}<span class="ampersand">&</span>{{person2Name}}</span>
            <p class="families">{{person1Family}} & {{person2Family}}</p>
        </div>
        <div class="gold-divider"></div>
        <div class="details-box">
            <div class="detail-row"><p class="detail-label">Save the Date</p><p class="detail-value">{{eventDate}}</p></div>
            <div class="detail-row"><p class="detail-label">Time</p><p class="detail-value">{{eventTime}}</p></div>
            <div class="detail-row"><p class="detail-label">Venue</p><p class="detail-value">{{venue}}</p></div>
        </div>
        <p class="message">{{message}}</p>
        <div class="gold-divider"></div>
        <div class="floral-bottom">❋</div>
    </div>
</body>
</html>'''


ROMANTIC_PINK_HTML = '''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Wedding Invitation</title>
    <link href="https://fonts.googleapis.com/css2?family=Cormorant+Garamond:wght@400;500;600;700&family=Quicksand:wght@300;400;500&display=swap" rel="stylesheet">
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { font-family: 'Quicksand', sans-serif; background: linear-gradient(135deg, #fdf2f8 0%, #fce7f3 50%, #fdf2f8 100%); min-height: 100vh; display: flex; justify-content: center; align-items: center; padding: 20px; }
        .invitation-card { background: #ffffff; max-width: 550px; width: 100%; padding: 50px 40px; border-radius: 20px; box-shadow: 0 20px 60px rgba(236, 72, 153, 0.15); position: relative; }
        .pink-accent { position: absolute; top: -3px; left: -3px; right: -3px; bottom: -3px; background: linear-gradient(135deg, #f9a8d4, #f472b6, #ec4899); border-radius: 22px; z-index: -1; opacity: 0.3; }
        .header { text-align: center; margin-bottom: 30px; }
        .floral { font-size: 36px; margin-bottom: 15px; }
        .subtitle { font-size: 12px; letter-spacing: 5px; text-transform: uppercase; color: #ec4899; }
        .couple-names { text-align: center; margin: 30px 0; }
        .names { font-family: 'Cormorant Garamond', serif; font-size: 44px; color: #4a1942; line-height: 1.2; }
        .ampersand { font-family: 'Great Vibes', cursive; font-size: 40px; color: #ec4899; display: block; margin: 5px 0; }
        .families { font-size: 13px; color: #9f7aea; margin-top: 15px; }
        .image-container { width: 140px; height: 140px; border-radius: 50%; overflow: hidden; margin: 25px auto; border: 4px solid #fbcfe8; display: none; }
        .image-container.visible { display: block; }
        .image-container img { width: 100%; height: 100%; object-fit: cover; }
        .details { background: linear-gradient(135deg, #fdf2f8, #fce7f3); padding: 25px; border-radius: 15px; text-align: center; margin: 25px 0; }
        .date { font-family: 'Cormorant Garamond', serif; font-size: 26px; color: #4a1942; margin-bottom: 8px; }
        .time { font-size: 16px; color: #9f7aea; margin-bottom: 10px; }
        .venue { font-size: 14px; color: #6b7280; line-height: 1.5; }
        .message { font-family: 'Cormorant Garamond', serif; font-size: 16px; color: #6b7280; font-style: italic; text-align: center; line-height: 1.8; margin: 25px 0; }
        .footer { text-align: center; font-size: 11px; color: #9ca3af; letter-spacing: 2px; }
    </style>
</head>
<body>
    <div class="invitation-card">
        <div class="pink-accent"></div>
        <div class="header">
            <div class="floral">🌸</div>
            <p class="subtitle">Wedding Celebration</p>
        </div>
        <div class="image-container"><img src="{{imageUrl}}" alt="Couple" /></div>
        <div class="couple-names">
            <span class="names">{{person1Name}}<span class="ampersand">&</span>{{person2Name}}</span>
            <p class="families">{{person1Family}} & {{person2Family}}</p>
        </div>
        <div class="details">
            <p class="date">{{eventDate}}</p>
            <p class="time">{{eventTime}}</p>
            <p class="venue">{{venue}}</p>
        </div>
        <p class="message">{{message}}</p>
        <p class="footer">Together with their families</p>
    </div>
</body>
</html>'''


BIRTHDAY_PARTY_HTML = '''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Birthday Invitation</title>
    <link href="https://fonts.googleapis.com/css2?family=Poppins:wght@400;500;600;700&display=swap" rel="stylesheet">
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { font-family: 'Poppins', sans-serif; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); min-height: 100vh; display: flex; justify-content: center; align-items: center; padding: 20px; }
        .invitation-card { background: linear-gradient(135deg, #ffffff 0%, #f8fafc 100%); max-width: 500px; width: 100%; padding: 45px 35px; border-radius: 20px; box-shadow: 0 25px 50px rgba(0, 0, 0, 0.2); text-align: center; position: relative; overflow: hidden; }
        .confetti { position: absolute; top: 0; left: 0; right: 0; height: 100px; background: linear-gradient(180deg, rgba(255,255,255,0.1) 0%, transparent 100%); }
        .badge { background: linear-gradient(135deg, #f97316, #ea580c); color: white; display: inline-block; padding: 5px 20px; border-radius: 20px; font-size: 12px; font-weight: 600; letter-spacing: 2px; margin-bottom: 20px; }
        .title { font-size: 42px; font-weight: 700; background: linear-gradient(135deg, #667eea, #764ba2); -webkit-background-clip: text; background-clip: text; -webkit-text-fill-color: transparent; }
        .name { font-size: 48px; font-weight: 700; color: #1e293b; margin: 15px 0; }
        .turns { font-size: 18px; color: #64748b; margin-bottom: 25px; }
        .turns span { font-weight: 700; color: #f97316; }
        .details-box { background: linear-gradient(135deg, #f1f5f9, #e2e8f0); padding: 20px; border-radius: 12px; margin: 20px 0; }
        .detail { margin: 10px 0; }
        .detail-label { font-size: 11px; text-transform: uppercase; letter-spacing: 2px; color: #94a3b8; }
        .detail-value { font-size: 16px; font-weight: 600; color: #334155; }
        .message { font-size: 14px; color: #64748b; line-height: 1.6; margin: 20px 0; }
        .rsvp { display: inline-block; background: linear-gradient(135deg, #667eea, #764ba2); color: white; padding: 12px 30px; border-radius: 25px; font-weight: 600; text-decoration: none; margin-top: 15px; }
        .emoji { font-size: 40px; margin-bottom: 15px; }
    </style>
</head>
<body>
    <div class="invitation-card">
        <div class="confetti"></div>
        <div class="emoji">🎂</div>
        <p class="badge">YOU'RE INVITED!</p>
        <h1 class="title">Birthday Party</h1>
        <p class="name">{{person1Name}}</p>
        <p class="turns">Is turning <span>{{eventDate}}</span></p>
        <div class="details-box">
            <div class="detail"><p class="detail-label">When</p><p class="detail-value">{{eventTime}}</p></div>
            <div class="detail"><p class="detail-label">Where</p><p class="detail-value">{{venue}}</p></div>
        </div>
        <p class="message">{{message}}</p>
        <a href="#" class="rsvp">RSVP Now</a>
    </div>
</body>
</html>'''


BABY_SHOWER_HTML = '''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Baby Shower Invitation</title>
    <link href="https://fonts.googleapis.com/css2?family=Nunito:wght@400;600;700&family=Dancing+Script:wght@500;600&display=swap" rel="stylesheet">
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { font-family: 'Nunito', sans-serif; background: linear-gradient(135deg, #fce7f3 0%, #fdf2f8 100%); min-height: 100vh; display: flex; justify-content: center; align-items: center; padding: 20px; }
        .invitation-card { background: #ffffff; max-width: 500px; width: 100%; padding: 45px 35px; border-radius: 20px; box-shadow: 0 20px 50px rgba(236, 72, 153, 0.15); text-align: center; position: relative; }
        .border-circle { position: absolute; top: 15px; left: 15px; right: 15px; bottom: 15px; border: 3px solid #fbcfe8; border-radius: 15px; pointer-events: none; }
        .title { font-size: 14px; letter-spacing: 6px; text-transform: uppercase; color: #ec4899; margin-bottom: 20px; }
        .main-title { font-family: 'Dancing Script', cursive; font-size: 48px; color: #be185d; margin-bottom: 10px; }
        .subtitle { font-size: 16px; color: #9f7aea; margin-bottom: 25px; }
        .baby-icon { font-size: 60px; margin: 20px 0; }
        .parent-name { font-size: 32px; font-weight: 700; color: #4a1942; margin: 20px 0; }
        .details { background: linear-gradient(135deg, #fdf2f8, #fce7f3); padding: 20px; border-radius: 12px; margin: 20px 0; }
        .detail { margin: 12px 0; }
        .detail-label { font-size: 10px; letter-spacing: 3px; text-transform: uppercase; color: #ec4899; }
        .detail-value { font-size: 18px; font-weight: 600; color: #4a1942; }
        .message { font-size: 14px; color: #6b7280; line-height: 1.6; margin: 20px 0; font-style: italic; }
        .footer { font-size: 12px; color: #9ca3af; margin-top: 20px; }
    </style>
</head>
<body>
    <div class="invitation-card">
        <div class="border-circle"></div>
        <p class="title">You're Invited</p>
        <h1 class="main-title">Baby Shower</h1>
        <p class="subtitle">Celebrating the arrival of</p>
        <div class="baby-icon">👶</div>
        <p class="parent-name">{{person1Name}}</p>
        <div class="details">
            <div class="detail"><p class="detail-label">When</p><p class="detail-value">{{eventDate}} • {{eventTime}}</p></div>
            <div class="detail"><p class="detail-label">Where</p><p class="detail-value">{{venue}}</p></div>
        </div>
        <p class="message">{{message}}</p>
        <p class="footer">Hosted by {{person2Family}}</p>
    </div>
</body>
</html>'''


CORPORATE_HTML = '''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Corporate Event Invitation</title>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap" rel="stylesheet">
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { font-family: 'Inter', sans-serif; background: #0f172a; min-height: 100vh; display: flex; justify-content: center; align-items: center; padding: 20px; }
        .invitation-card { background: #1e293b; max-width: 500px; width: 100%; padding: 45px 35px; border-radius: 12px; box-shadow: 0 25px 50px rgba(0, 0, 0, 0.4); border: 1px solid #334155; }
        .header { text-align: center; margin-bottom: 30px; padding-bottom: 25px; border-bottom: 1px solid #334155; }
        .logo-placeholder { width: 60px; height: 60px; background: linear-gradient(135deg, #3b82f6, #6366f1); border-radius: 10px; margin: 0 auto 20px; display: flex; align-items: center; justify-content: center; font-weight: 700; color: white; font-size: 24px; }
        .event-type { font-size: 11px; letter-spacing: 4px; text-transform: uppercase; color: #3b82f6; margin-bottom: 10px; }
        .title { font-size: 28px; font-weight: 700; color: #f8fafc; margin-bottom: 5px; }
        .subtitle { font-size: 14px; color: #94a3b8; }
        .host { margin: 25px 0; padding: 20px; background: #0f172a; border-radius: 8px; text-align: center; }
        .host-label { font-size: 10px; letter-spacing: 2px; text-transform: uppercase; color: #64748b; margin-bottom: 8px; }
        .host-name { font-size: 20px; font-weight: 600; color: #f8fafc; }
        .details { margin: 25px 0; }
        .detail-row { display: flex; justify-content: space-between; padding: 12px 0; border-bottom: 1px solid #334155; }
        .detail-row:last-child { border-bottom: none; }
        .detail-label { font-size: 12px; color: #64748b; }
        .detail-value { font-size: 14px; font-weight: 500; color: #f8fafc; text-align: right; }
        .message { font-size: 13px; color: #94a3b8; line-height: 1.6; margin: 20px 0; text-align: center; }
        .cta { display: block; width: 100%; padding: 14px; background: linear-gradient(135deg, #3b82f6, #6366f1); color: white; text-align: center; border-radius: 8px; font-weight: 600; text-decoration: none; margin-top: 20px; }
    </style>
</head>
<body>
    <div class="invitation-card">
        <div class="header">
            <div class="logo-placeholder">📋</div>
            <p class="event-type">You're Invited</p>
            <h1 class="title">{{person1Name}}</h1>
            <p class="subtitle">{{person2Family}}</p>
        </div>
        <div class="details">
            <div class="detail-row"><span class="detail-label">Date</span><span class="detail-value">{{eventDate}}</span></div>
            <div class="detail-row"><span class="detail-label">Time</span><span class="detail-value">{{eventTime}}</span></div>
            <div class="detail-row"><span class="detail-label">Venue</span><span class="detail-value">{{venue}}</span></div>
        </div>
        <p class="message">{{message}}</p>
        <a href="#" class="cta">RSVP Now</a>
    </div>
</body>
</html>'''


UNIQUE_HTMLs = {
    "modern_minimal": MODERN_MINIMAL_HTML,
    "elegant_floral": ELEGANT_FLORAL_HTML,
    "luxury_dark": LUXURY_DARK_HTML,
    "romantic_pink": ROMANTIC_PINK_HTML,
    "birthday_party": BIRTHDAY_PARTY_HTML,
    "baby_shower": BABY_SHOWER_HTML,
    "corporate": CORPORATE_HTML,
}


TEMPLATES = [
    {
        "name": "Modern Minimal Wedding",
        "description": "Clean and elegant wedding design with dark theme and warm accents",
        "category": "modern",
        "tags": ["minimal", "elegant", "classic", "wedding", "dark"],
        "event_type": "wedding",
        "is_premium": False,
        "html_key": "modern_minimal",
    },
    {
        "name": "Classic Floral Wedding",
        "description": "Timeless elegant wedding with floral ornaments and beige tones",
        "category": "classic",
        "tags": ["floral", "elegant", "traditional", "wedding", "beige"],
        "event_type": "wedding",
        "is_premium": True,
        "price": 99.0,
        "html_key": "elegant_floral",
    },
    {
        "name": "Luxury Gold Wedding",
        "description": "Premium dark luxury wedding with gold accents and elegant typography",
        "category": "luxury",
        "tags": ["luxury", "gold", "premium", "wedding", "dark"],
        "event_type": "wedding",
        "is_premium": True,
        "price": 149.0,
        "html_key": "luxury_dark",
    },
    {
        "name": "Romantic Pink Wedding",
        "description": "Soft romantic wedding with pink flowers and feminine touches",
        "category": "romantic",
        "tags": ["romantic", "pink", "floral", "wedding", "soft"],
        "event_type": "wedding",
        "is_premium": False,
        "html_key": "romantic_pink",
    },
    {
        "name": "Vibrant Birthday Party",
        "description": "Colorful and fun birthday invitation with confetti theme",
        "category": "playful",
        "tags": ["colorful", "fun", "birthday", "party", "confetti"],
        "event_type": "birthday",
        "is_premium": False,
        "html_key": "birthday_party",
    },
    {
        "name": "Premium Birthday",
        "description": "Elegant birthday invitation with sophisticated purple gradient",
        "category": "elegant",
        "tags": ["elegant", "purple", "birthday", "premium"],
        "event_type": "birthday",
        "is_premium": True,
        "price": 79.0,
        "html_key": "birthday_party",
    },
    {
        "name": "Sweet Baby Shower",
        "description": "Soft pink gradient baby shower invitation with adorable design",
        "category": "soft",
        "tags": ["soft", "pink", "baby", "shower", "adorable"],
        "event_type": "baby_shower",
        "is_premium": False,
        "html_key": "baby_shower",
    },
    {
        "name": "Premium Baby Shower",
        "description": "Elegant baby shower with sophisticated design",
        "category": "elegant",
        "tags": ["elegant", "baby", "shower", "premium"],
        "event_type": "baby_shower",
        "is_premium": True,
        "price": 69.0,
        "html_key": "baby_shower",
    },
    {
        "name": "Elegant Engagement",
        "description": "Sophisticated engagement ceremony with blue and navy theme",
        "category": "elegant",
        "tags": ["elegant", "engagement", "navy", "blue", "romantic"],
        "event_type": "engagement",
        "is_premium": True,
        "price": 89.0,
        "html_key": "modern_minimal",
    },
    {
        "name": "Golden Anniversary",
        "description": "Celebrate milestone anniversaries with warm golden tones",
        "category": "celebration",
        "tags": ["anniversary", "celebration", "golden", "love"],
        "event_type": "anniversary",
        "is_premium": False,
        "html_key": "elegant_floral",
    },
    {
        "name": "Graduation Ceremony",
        "description": "Proud graduation invitation with academic blue theme",
        "category": "academic",
        "tags": ["graduation", "academic", "celebration", "blue"],
        "event_type": "graduation",
        "is_premium": False,
        "html_key": "corporate",
    },
    {
        "name": "Corporate Event",
        "description": "Professional corporate event invitation with clean design",
        "category": "corporate",
        "tags": ["corporate", "professional", "business", "event"],
        "event_type": "corporate",
        "is_premium": False,
        "html_key": "corporate",
    },
]


async def seed_templates():
    import shutil
    
    print("=" * 60)
    print("WCard Template Seeder (Content-Based Hashing)")
    print("=" * 60)
    
    print("\n⚠️  WARNING: This will delete ALL existing data:")
    print("    - thumbnails/ folder")
    print("    - templates/ folder")
    print("    - All templates in database")
    print()
    response = input("Do you want to continue? (yes/no): ").strip().lower()
    
    if response not in ['yes', 'y']:
        print("\n❌ Seed cancelled.")
        return
    
    print("\n[0/4] Cleaning up old data...")
    THUMBNAILS_DIR = Path("thumbnails")
    TEMPLATES_DIR = Path("templates")
    
    if THUMBNAILS_DIR.exists():
        shutil.rmtree(THUMBNAILS_DIR)
        print(f"    [+] Deleted: thumbnails/")
    else:
        print(f"    [=] thumbnails/ not found")
    
    if TEMPLATES_DIR.exists():
        shutil.rmtree(TEMPLATES_DIR)
        print(f"    [+] Deleted: templates/")
    else:
        print(f"    [=] templates/ not found")
    
    client = AsyncIOMotorClient(settings.mongodb_url)
    db = client[settings.database_name]
    collection = db["templates"]
    
    print(f"\nConnecting to: {settings.mongodb_url}")
    print(f"Database: {settings.database_name}")
    
    result = await collection.delete_many({})
    print(f"    [+] Cleared {result.deleted_count} templates from database")
    
    html_files_saved = {}
    thumbnails_generated = {}
    
    print("\n[1/4] Saving unique HTML files...")
    for html_key, html_content in UNIQUE_HTMLs.items():
        content_hash, is_new = save_template(html_content)
        html_files_saved[html_key] = content_hash
        if is_new:
            print(f"    [+] Saved: {content_hash}.html")
        else:
            print(f"    [=] Reused: {content_hash}.html")
    
    print("\n[2/4] Generating thumbnails...")
    for html_key, html_content in UNIQUE_HTMLs.items():
        content_hash = html_files_saved[html_key]
        try:
            thumb_path = await generate_thumbnail(html_content, content_hash)
            thumbnails_generated[html_key] = thumb_path
            if thumb_path:
                print(f"    [+] Thumbnail: {thumb_path}")
            else:
                print(f"    [!] Thumbnail skipped (Playwright may not be installed)")
        except Exception as e:
            print(f"    [!] Thumbnail error: {e}")
    
    print("\n[3/4] Creating template documents...")
    now = datetime.utcnow()
    success_count = 0
    
    for i, template in enumerate(TEMPLATES, 1):
        html_key = template["html_key"]
        content_hash = html_files_saved[html_key]
        
        print(f"\n[{i}/{len(TEMPLATES)}] {template['name']}")
        print(f"    [=] Reusing HTML: {content_hash}.html")
        
        template_doc = {
            "name": template["name"],
            "description": template["description"],
            "category": template["category"],
            "tags": template["tags"],
            "event_type": template["event_type"],
            "is_premium": template["is_premium"],
            "price": template.get("price"),
            "supports_image": supports_image_feature(UNIQUE_HTMLs[html_key]),
            "content_hash": content_hash,
            "created_at": now,
            "updated_at": now,
        }
        
        try:
            await collection.insert_one(template_doc)
            print(f"    [+] Saved to database")
            success_count += 1
        except Exception as e:
            print(f"    [!] Error: {e}")
    
    unique_files = len(set(html_files_saved.values()))
    print("\n" + "=" * 60)
    print(f"Seeding Complete!")
    print(f"  [+] Templates: {success_count}")
    print(f"  [+] Unique HTML files: {unique_files}")
    print(f"  [+] Reused templates: {len(TEMPLATES) - success_count + (success_count - unique_files)}")
    print("=" * 60)
    
    client.close()


if __name__ == "__main__":
    print("\nStarting seed process...")
    asyncio.run(seed_templates())
