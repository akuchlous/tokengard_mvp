/**
 * TokenGuard - Authentication JavaScript
 * 
 * This file handles all authentication-related functionality including:
 * - User registration with validation
 * - User login with JWT token management
 * - Password strength checking
 * - Form validation and error handling
 * - Integration with common utilities
 * 
 * The code is designed to be maintainable, secure, and user-friendly.
 * It leverages the common utilities defined in common.js for consistency.
 */

/**
 * Authentication Manager Class
 * Handles all authentication-related functionality in a centralized manner
 */
class AuthManager {
    constructor() {
        this.currentForm = null;
        this.formElements = {};
        this.init();
    }
    
    /**
     * Initialize the authentication manager
     * Sets up event listeners and form handling based on current page
     */
    init() {
        // Wait for common utilities to be available
        if (typeof window.messageDisplay === 'undefined') {
            setTimeout(() => this.init(), 100);
            return;
        }
        
        // Initialize based on current page
        if (document.getElementById('registerForm')) {
            this.initRegistration();
        } else if (document.getElementById('loginForm')) {
            this.initLogin();
        }
        
        // Initialize password strength checker
        this.initPasswordStrength();
        
        console.log('AuthManager initialized for:', this.currentForm || 'unknown page');
    }
    
    /**
     * Initialize registration form functionality
     * Sets up validation, event listeners, and form submission handling
     */
    initRegistration() {
        this.currentForm = 'register';
        
        // Cache form elements for better performance
        this.formElements = {
            form: document.getElementById('registerForm'),
            email: document.getElementById('email'),
            password: document.getElementById('password'),
            confirmPassword: document.getElementById('confirmPassword'),
            submitBtn: document.getElementById('submitBtn')
        };
        
        // Set up real-time validation with debouncing for better performance
        const debouncedEmailValidation = debounce(() => this.validateEmail(), 300);
        const debouncedPasswordStrength = debounce(() => this.checkPasswordStrength(), 200);
        
        // Add event listeners
        safeAddEventListener(this.formElements.email, 'blur', debouncedEmailValidation);
        safeAddEventListener(this.formElements.password, 'input', debouncedPasswordStrength);
        safeAddEventListener(this.formElements.confirmPassword, 'blur', () => this.validatePasswordMatch());
        safeAddEventListener(this.formElements.form, 'submit', (e) => this.handleRegistration(e));
        
        console.log('Registration form initialized');
    }
    
    /**
     * Initialize login form functionality
     * Sets up validation and form submission handling
     */
    initLogin() {
        this.currentForm = 'login';
        
        // Cache form elements
        this.formElements = {
            form: document.getElementById('loginForm'),
            email: document.getElementById('email'),
            password: document.getElementById('password'),
            submitBtn: document.getElementById('submitBtn')
        };
        
        // Set up validation
        const debouncedEmailValidation = debounce(() => this.validateEmail(), 300);
        safeAddEventListener(this.formElements.email, 'blur', debouncedEmailValidation);
        safeAddEventListener(this.formElements.form, 'submit', (e) => this.handleLogin(e));
        
        console.log('Login form initialized');
    }
    
    /**
     * Initialize password strength checker
     * Provides real-time feedback on password strength
     */
    initPasswordStrength() {
        const passwordInput = this.formElements.password;
        if (!passwordInput) return;
        
        // Password strength is already handled in initRegistration
        // This method exists for potential future expansion
    }
    
    /**
     * Validate email input using common utilities
     * @returns {boolean} - True if email is valid
     */
    validateEmail() {
        const email = this.formElements.email.value.trim();
        const errorElement = document.getElementById('emailError');
        
        if (!email) {
            this.showFieldError('email', 'Email is required');
            return false;
        }
        
        if (!isValidEmail(email)) {
            this.showFieldError('email', 'Please enter a valid email address');
            return false;
        }
        
        this.clearFieldError('email');
        return true;
    }
    
    /**
     * Check password strength and display feedback
     * Uses common validation utilities for consistency
     */
    checkPasswordStrength() {
        const password = this.formElements.password.value;
        const strengthElement = document.getElementById('passwordStrength');
        
        if (!strengthElement) return;
        
        const validation = validatePassword(password);
        
        // Update strength display
        strengthElement.textContent = validation.message;
        strengthElement.className = `form-message ${this.getStrengthClass(validation.strength)}`;
        
        // Show suggestions if password is weak
        if (validation.suggestions.length > 0) {
            const suggestionsElement = document.getElementById('passwordSuggestions');
            if (suggestionsElement) {
                suggestionsElement.innerHTML = validation.suggestions.map(s => `<li>${s}</li>`).join('');
            }
        }
    }
    
    /**
     * Get CSS class for password strength display
     * @param {number} strength - Password strength score
     * @returns {string} - CSS class name
     */
    getStrengthClass(strength) {
        if (strength <= 2) return 'error';
        if (strength === 3) return 'warning';
        return 'success';
    }
    
    /**
     * Validate password confirmation match
     * @returns {boolean} - True if passwords match
     */
    validatePasswordMatch() {
        const password = this.formElements.password.value;
        const confirmPassword = this.formElements.confirmPassword.value;
        
        const validation = validatePasswordMatch(password, confirmPassword);
        
        if (!validation.isValid) {
            this.showFieldError('confirmPassword', validation.message);
            return false;
        }
        
        this.clearFieldError('confirmPassword');
        return true;
    }
    
    /**
     * Show field-specific error message
     * @param {string} fieldName - Name of the field with error
     * @param {string} message - Error message to display
     */
    showFieldError(fieldName, message) {
        const input = this.formElements[fieldName];
        const errorElement = document.getElementById(fieldName + 'Error');
        
        if (input) {
            input.classList.add('error');
        }
        
        if (errorElement) {
            errorElement.textContent = message;
            errorElement.className = 'form-message error';
        }
    }
    
    /**
     * Clear field-specific error message
     * @param {string} fieldName - Name of the field to clear error for
     */
    clearFieldError(fieldName) {
        const input = this.formElements[fieldName];
        const errorElement = document.getElementById(fieldName + 'Error');
        
        if (input) {
            input.classList.remove('error');
        }
        
        if (errorElement) {
            errorElement.textContent = '';
            errorElement.className = 'form-message';
        }
    }
    
    /**
     * Show message using common message display system
     * @param {string} message - Message to display
     * @param {string} type - Message type (success, error, info, warning)
     */
    showMessage(message, type = 'info') {
        if (window.messageDisplay) {
            window.messageDisplay.show(message, type);
        } else {
            // Fallback to local message display
            const messageElement = document.getElementById('message');
            if (messageElement) {
                messageElement.textContent = message;
                messageElement.className = `message ${type}`;
                messageElement.style.display = 'block';
                
                setTimeout(() => {
                    messageElement.style.display = 'none';
                }, 5000);
            }
        }
    }
    
    /**
     * Set loading state using common loading manager
     * @param {boolean} loading - Whether to show loading state
     * @param {string} loadingText - Text to show during loading
     */
    setLoading(loading, loadingText = 'Processing...') {
        if (window.loadingManager && this.formElements.submitBtn) {
            window.loadingManager.setLoading(this.formElements.submitBtn, loading, loadingText);
        } else {
            // Fallback loading state
            const submitBtn = this.formElements.submitBtn;
            if (submitBtn) {
                if (loading) {
                    submitBtn.classList.add('loading');
                    submitBtn.disabled = true;
                } else {
                    submitBtn.classList.remove('loading');
                    submitBtn.disabled = false;
                }
            }
        }
    }
    
    /**
     * Handle user registration form submission
     * @param {Event} e - Form submission event
     */
    async handleRegistration(e) {
        e.preventDefault();
        
        // Validate all fields
        const emailValid = this.validateEmail();
        const passwordValid = this.validatePasswordMatch();
        
        if (!emailValid || !passwordValid) {
            this.showMessage('Please fix the errors above', 'error');
            return;
        }
        
        // Prepare form data
        const formData = {
            email: this.formElements.email.value.trim(),
            password: this.formElements.password.value
        };
        
        this.setLoading(true, 'Creating Account...');
        
        try {
            const response = await this.makeApiRequest('/auth/register', formData);
            
            if (response.success) {
                this.showMessage(response.data.message, 'success');
                
                // Redirect to login after successful registration
                setTimeout(() => {
                    window.location.href = '/auth/login';
                }, 2000);
            } else {
                this.showMessage(response.error || 'Registration failed', 'error');
            }
        } catch (error) {
            console.error('Registration error:', error);
            this.showMessage('Registration failed. Please try again.', 'error');
        } finally {
            this.setLoading(false);
        }
    }
    
    /**
     * Handle user login form submission
     * @param {Event} e - Form submission event
     */
    async handleLogin(e) {
        e.preventDefault();
        
        // Validate email
        if (!this.validateEmail()) {
            this.showMessage('Please fix the errors above', 'error');
            return;
        }
        
        // Prepare form data
        const formData = {
            email: this.formElements.email.value.trim(),
            password: this.formElements.password.value
        };
        
        this.setLoading(true, 'Signing In...');
        
        try {
            const response = await this.makeApiRequest('/auth/login', formData);
            
            if (response.success) {
                // Store JWT token securely
                this.storeAuthToken(response.data.token);
                
                this.showMessage(response.data.message, 'success');
                
                // Redirect to dashboard
                setTimeout(() => {
                    window.location.href = response.data.redirect_url;
                }, 1000);
            } else {
                this.showMessage(response.error || 'Login failed', 'error');
            }
        } catch (error) {
            console.error('Login error:', error);
            this.showMessage('Login failed. Please try again.', 'error');
        } finally {
            this.setLoading(false);
        }
    }
    
    /**
     * Make API request with error handling
     * @param {string} endpoint - API endpoint
     * @param {Object} data - Request data
     * @returns {Object} - Response object with success/error information
     */
    async makeApiRequest(endpoint, data) {
        try {
            const response = await fetch(endpoint, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(data)
            });
            
            const responseData = await response.json();
            
            if (response.ok) {
                return { success: true, data: responseData };
            } else {
                return { success: false, error: responseData.error || 'Request failed' };
            }
        } catch (error) {
            console.error('API request failed:', error);
            return { success: false, error: 'Network error. Please check your connection.' };
        }
    }
    
    /**
     * Store authentication token securely
     * @param {string} token - JWT token to store
     */
    storeAuthToken(token) {
        try {
            // In production, consider using httpOnly cookies or secure storage
            localStorage.setItem('authToken', token);
            
            // Set token expiration (optional)
            const expiration = new Date();
            expiration.setHours(expiration.getHours() + 1); // 1 hour
            localStorage.setItem('authTokenExpiration', expiration.toISOString());
            
            console.log('Auth token stored successfully');
        } catch (error) {
            console.error('Failed to store auth token:', error);
        }
    }
    
    /**
     * Get stored authentication token
     * @returns {string|null} - Stored token or null if not found/expired
     */
    getAuthToken() {
        try {
            const token = localStorage.getItem('authToken');
            const expiration = localStorage.getItem('authTokenExpiration');
            
            if (!token) return null;
            
            // Check if token is expired
            if (expiration && new Date() > new Date(expiration)) {
                this.clearAuthToken();
                return null;
            }
            
            return token;
        } catch (error) {
            console.error('Failed to get auth token:', error);
            return null;
        }
    }
    
    /**
     * Clear stored authentication token
     */
    clearAuthToken() {
        try {
            localStorage.removeItem('authToken');
            localStorage.removeItem('authTokenExpiration');
            console.log('Auth token cleared');
        } catch (error) {
            console.error('Failed to clear auth token:', error);
        }
    }
}

// Initialize authentication manager when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    new AuthManager();
});
