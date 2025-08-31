# Security Documentation

## 🔒 **Security Overview**

TokenGuard implements different security levels for development and production environments to balance security with development convenience.

## 🚀 **Production Environment (AWS)**

### **HTTPS & SSL**
- ✅ **SSL Certificate**: AWS Certificate Manager (ACM) provides free SSL certificates
- ✅ **HTTPS Only**: All production traffic is encrypted
- ✅ **Domain**: `tokengard.com` with proper SSL validation
- ✅ **CloudFront**: Global CDN with HTTPS termination
- ✅ **HSTS**: HTTP Strict Transport Security headers

### **Email Security**
- ✅ **TLS Encryption**: `MAIL_USE_TLS=True` (port 587)
- ✅ **Secure SMTP**: Uses Gmail's secure SMTP with app passwords
- ✅ **No Plain Text**: All email communication is encrypted
- ✅ **App Passwords**: Uses Gmail app-specific passwords (not account passwords)

### **Database Security**
- ✅ **PostgreSQL**: Production-grade database with encryption
- ✅ **Encrypted Connections**: Database connections are encrypted
- ✅ **Environment Variables**: All secrets stored securely in AWS
- ✅ **IAM Roles**: AWS IAM roles for secure access

### **Session Security**
- ✅ **Secure Cookies**: `SESSION_COOKIE_SECURE = True`
- ✅ **HTTP Only**: `SESSION_COOKIE_HTTPONLY = True`
- ✅ **SameSite**: `SESSION_COOKIE_SAMESITE = 'Lax'`
- ✅ **JWT Tokens**: Secure JWT tokens with expiration

## 🖥️ **Development Environment**

### **Current Security Level**
- ✅ **HTTP Only**: Development runs on `http://127.0.0.1:5000` (acceptable for local dev)
- ✅ **Local Network**: Only accessible on localhost (127.0.0.1) by default
- ⚠️ **Debug Mode**: `DEBUG = True` (shows sensitive information - normal for dev)
- 🔧 **HTTPS Optional**: Self-signed certificates available if needed for testing

### **Email Security in Development**
- ✅ **TLS Enabled**: `MAIL_USE_TLS=True` by default
- ✅ **Secure SMTP**: Uses Gmail's secure SMTP
- ⚠️ **Local Testing**: Consider using Mailtrap for development

## 🛡️ **Security Features**

### **Password Security**
- ✅ **Bcrypt Hashing**: `BCRYPT_LOG_ROUNDS=12` (production strength)
- ✅ **Salt Generation**: Unique salt for each password
- ✅ **No Plain Text Storage**: Passwords are never stored in plain text

### **JWT Security**
- ✅ **Secret Keys**: Environment-specific JWT secret keys
- ✅ **Token Expiration**: Configurable expiration times
- ✅ **Secure Storage**: Tokens stored in localStorage (consider httpOnly cookies for production)

### **Rate Limiting**
- ✅ **Registration Limits**: Prevents spam registrations
- ✅ **Login Attempts**: Limits brute force attacks
- ✅ **API Rate Limiting**: Protects against abuse

### **Input Validation**
- ✅ **SQL Injection Protection**: Parameterized queries
- ✅ **XSS Protection**: Input sanitization
- ✅ **CSRF Protection**: Form validation tokens

## 🔧 **Development HTTPS Setup**

### **Option 1: Self-Signed Certificates (Optional)**
```bash
# Generate SSL certificates (only if you need HTTPS for testing)
./setup_dev_https.sh

# Run with HTTPS
make run-dev-https
```

**Note**: HTTPS is optional for local development. Plain HTTP on localhost is perfectly secure and much simpler.

### **Option 2: Use Production-like Environment**
```bash
# Use production config locally
make run-prod
```

## 📧 **Email Security Best Practices**

### **Development**
- Use Mailtrap or similar service for testing
- Never use real email credentials in development
- Test email functionality with mock services
- **HTTP is fine**: Local development on localhost doesn't need HTTPS

### **Production**
- Use dedicated email service (SendGrid, AWS SES, etc.)
- Implement email verification workflows
- Monitor email delivery and bounce rates

## 🚨 **Security Checklist**

### **Before Production Deployment**
- [ ] Change all default secret keys
- [ ] Enable HTTPS only
- [ ] Set secure cookie flags
- [ ] Configure proper CORS policies
- [ ] Set up monitoring and logging
- [ ] Implement rate limiting
- [ ] Test security features
- [ ] Review access controls

### **For Local Development**
- [x] HTTP on localhost is perfectly fine
- [x] Debug mode is acceptable for development
- [x] Local database is fine for testing
- [x] No need for SSL certificates locally

### **Ongoing Security**
- [ ] Regular security updates
- [ ] Monitor for suspicious activity
- [ ] Regular security audits
- [ ] Keep dependencies updated
- [ ] Monitor AWS CloudTrail logs

## 🔍 **Security Testing**

### **Automated Tests**
```bash
# Run security-specific tests
make test-security

# Run all tests with coverage
make test-all
```

### **Manual Security Testing**
- Test authentication flows
- Verify HTTPS enforcement
- Check for information disclosure
- Test rate limiting
- Verify input validation

## 📚 **Additional Resources**

- [OWASP Top 10](https://owasp.org/www-project-top-ten/)
- [Flask Security Documentation](https://flask-security.readthedocs.io/)
- [AWS Security Best Practices](https://aws.amazon.com/security/security-learning/)
- [JWT Security Best Practices](https://auth0.com/blog/a-look-at-the-latest-draft-for-jwt-bcp/)

## 🆘 **Security Issues**

If you discover a security vulnerability:
1. **DO NOT** create a public issue
2. Email security@tokengard.com (if available)
3. Follow responsible disclosure practices
4. Wait for acknowledgment before public disclosure
