# MyHighlights - Login Guide

## 🔐 How to Login

### Standard Login (No 2FA)

**If you DON'T have 2FA enabled on Instagram:**

1. Enter your **username**
2. Enter your **password**
3. **Leave 2FA field EMPTY** ✅
4. Click **"Log In"**

That's it! The app will log you in without asking for a 2FA code.

---

### Login with 2FA

**If you DO have 2FA enabled on Instagram:**

1. Enter your **username**
2. Enter your **password**
3. Click **"Log In"**
4. Instagram will ask for 2FA
5. Get the 6-digit code from your authenticator app
6. Enter the code in the **"2FA Code (optional)"** field
7. Click **"Log In"** again

---

## 📱 Getting Your 2FA Code

If Instagram requires 2FA, you'll get the code from:

- **Authenticator app** (Google Authenticator, Authy, etc.)
- **SMS** (if you set up SMS 2FA)
- **Email** (in some cases)

The code is usually **6 digits** and expires after 30-60 seconds.

---

## ✅ What Happens After Login

Once logged in successfully:

1. ✅ Session is **saved automatically**
2. ✅ Status changes to **"● Logged in"**
3. ✅ Login fields become **disabled**
4. ✅ **"Log Out"** button appears
5. ✅ You can now **download highlights**!

**Next time you open the app**, you'll be logged in automatically - no need to enter credentials again!

---

## 🔄 Session Management

### Auto-Login
- Your session is saved in `data/.session/instagram_session.json`
- When you restart the app, it tries to restore your session
- If the session is still valid, you're logged in automatically
- If expired, you'll need to log in again

### Manual Logout
- Click **"Log Out"** button
- Session is cleared
- Login fields are enabled again
- You'll need to log in next time

---

## ❌ Common Login Issues

### Issue: "2FA code required"

**Cause**: You have 2FA enabled but didn't enter the code

**Solution**:
1. Get your 6-digit code from authenticator app
2. Enter it in the "2FA Code (optional)" field
3. Click "Log In" again

---

### Issue: "Invalid username or password"

**Cause**: Wrong credentials

**Solution**:
1. Double-check your username (no @ symbol)
2. Make sure Caps Lock is off
3. Try logging in to Instagram.com to verify credentials
4. Try again in the app

---

### Issue: "Challenge required"

**Cause**: Instagram needs you to verify your account

**Solution**:
1. Open Instagram.com in your browser
2. Log in there
3. Complete any security challenges
4. Try the app again after a few minutes

---

### Issue: Login works but session doesn't persist

**Cause**: Session file not being saved

**Solution**:
1. Check that `data/.session/` folder exists
2. Make sure you have write permissions
3. Try deleting `data/.session/instagram_session.json`
4. Log in again

---

## 🔒 Security Tips

### ✅ DO:
- Use your real Instagram credentials
- Keep your session file safe
- Log out when sharing your computer
- Use a strong password

### ❌ DON'T:
- Share your session file with others
- Use the app on untrusted computers
- Store your password anywhere in plain text
- Give your 2FA codes to anyone

---

## 🎯 Quick Login Examples

### Example 1: First-time login (no 2FA)
```
1. Username: myusername
2. Password: ••••••••
3. 2FA Code: [LEAVE EMPTY]
4. Click "Log In"
✅ Logged in!
```

### Example 2: First-time login (with 2FA)
```
1. Username: myusername
2. Password: ••••••••
3. 2FA Code: [LEAVE EMPTY]
4. Click "Log In"
❌ Error: "2FA code required"

5. Get code from authenticator: 123456
6. Enter in 2FA field: 123456
7. Click "Log In"
✅ Logged in!
```

### Example 3: Returning user (session saved)
```
1. Open app
✅ Already logged in!
   (Session restored automatically)
```

---

## 🆘 Still Having Issues?

1. **Clear your session:**
   ```bash
   rm -rf data/.session/
   ```

2. **Try with verbose output:**
   ```bash
   python main.py
   ```
   (Check console for error messages)

3. **Verify Instagram account:**
   - Make sure you can log in to Instagram.com
   - Complete any security challenges
   - Wait a few hours if you got rate-limited

4. **Check dependencies:**
   ```bash
   pip install --upgrade aiograpi
   ```

---

## 📝 Troubleshooting Checklist

Before asking for help, verify:

- [ ] Username is correct (no @ symbol)
- [ ] Password is correct (try on Instagram.com first)
- [ ] 2FA code is current (if using 2FA)
- [ ] Instagram account is not locked
- [ ] No active security challenges
- [ ] aiograpi is installed: `pip show aiograpi`
- [ ] Session folder exists: `ls -la data/.session/`
- [ ] You have write permissions

---

## 🎉 Success!

Once you see **"● Logged in"**, you're ready to download highlights!

Go to the "By Highlight Link" tab and paste your first highlight URL.

Happy downloading! 🎬
