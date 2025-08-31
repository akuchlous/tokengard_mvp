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
        console.log('AuthManager init called');
        
        // Wait for common utilities to be available
        if (typeof window.messageDisplay === 'undefined') {
            console.log('messageDisplay not ready, retrying in 100ms...');
            setTimeout(() => this.init(), 100);
            return;
        }
        
        console.log('messageDisplay is ready, initializing forms...');
        
        // Initialize based on current page
        if (document.getElementById('registerForm')) {
            console.log('Found register form, initializing...');
            this.initRegistration();
        } else if (document.getElementById('loginForm')) {
            console.log('Found login form, initializing...');
            this.initLogin();
        } else {
            console.log('No auth forms found on this page');
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
        console.log('initRegistration called');
        this.currentForm = 'register';
        
        // Cache form elements for better performance
        this.formElements = {
            form: document.getElementById('registerForm'),
            email: document.getElementById('email'),
            password: document.getElementById('password'),
            confirmPassword: document.getElementById('confirmPassword'),
            submitBtn: document.getElementById('submitBtn')
        };
        
        console.log('Form elements found:', {
            form: !!this.formElements.form,
            email: !!this.formElements.email,
            password: !!this.formElements.password,
            confirmPassword: !!this.formElements.confirmPassword,
            submitBtn: !!this.formElements.submitBtn
        });
        
        // Set up real-time validation with debouncing for better performance
        const debouncedEmailValidation = debounce(() => this.validateEmail(), 300);
        const debouncedPasswordStrength = debounce(() => this.checkPasswordStrength(), 200);
        
        // Add event listeners
        safeAddEventListener(this.formElements.email, 'blur', debouncedEmailValidation);
        safeAddEventListener(this.formElements.password, 'input', debouncedPasswordStrength);
        safeAddEventListener(this.formElements.confirmPassword, 'blur', () => this.validatePasswordMatch());
        
        // Use button click event as primary method since form submit isn't working reliably
        safeAddEventListener(this.formElements.submitBtn, 'click', (e) => {
            console.log('Submit button clicked!');
            e.preventDefault();
            e.stopPropagation();
            this.handleRegistration(e);
        });
        
        console.log('Registration form initialized successfully');
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
        console.log('handleRegistration called, preventing default...');
        e.preventDefault();
        
        console.log('Form data:', {
            email: this.formElements.email.value,
            password: this.formElements.password.value,
            confirmPassword: this.formElements.confirmPassword.value
        });
        
        // Validate all fields
        const emailValid = this.validateEmail();
        const passwordValid = this.validatePasswordMatch();
        
        if (!emailValid || !passwordValid) {
            console.log('Validation failed');
            this.showMessage('Please fix the errors above', 'error');
            return;
        }
        
        // Prepare form data
        const formData = {
            email: this.formElements.email.value.trim(),
            password: this.formElements.password.value
        };
        
        console.log('Making API request with data:', formData);
        this.setLoading(true, 'Creating Account...');
        
        try {
            const response = await this.makeApiRequest('/auth/register', formData);
            console.log('API response:', response);
            
            if (response.success) {
                this.showMessage(response.data.message, 'success');
                
                // Redirect to activation sent page after successful registration
                setTimeout(() => {
                    console.log('Redirecting to activation sent page...');
                    if (response.data.redirect_url) {
                        window.location.href = response.data.redirect_url;
                    } else {
                        // Fallback to activation sent page with email
                        const email = this.formElements.email.value.trim();
                        window.location.href = `/auth/activation-sent?email=${encodeURIComponent(email)}`;
                    }
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
                
                // Store the redirect URL and navigate programmatically
                // Use a longer delay to ensure token is properly stored
                setTimeout(() => {
                    console.log('About to navigate to protected route:', response.data.redirect_url);
                    console.log('Token stored:', !!this.getAuthToken());
                    this.navigateToProtectedRoute(response.data.redirect_url);
                }, 2000);
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
     * Make authenticated GET request with JWT token
     * @param {string} endpoint - API endpoint
     * @returns {Object} - Response object with success/error information
     */
    async makeAuthenticatedRequest(endpoint) {
        try {
            console.log('makeAuthenticatedRequest called for endpoint:', endpoint);
            const token = this.getAuthToken();
            console.log('Token found in makeAuthenticatedRequest:', !!token);
            
            if (!token) {
                console.log('No token found in makeAuthenticatedRequest');
                return { success: false, error: 'No authentication token found' };
            }

            console.log('Making fetch request with token...');
            const response = await fetch(endpoint, {
                method: 'GET',
                headers: {
                    'Authorization': `Bearer ${token}`,
                    'Content-Type': 'application/json',
                    'X-Requested-With': 'XMLHttpRequest'
                }
            });
            
            console.log('Response status:', response.status);
            const responseData = await response.json();
            console.log('Response data:', responseData);
            
            if (response.ok) {
                return { success: true, data: responseData };
            } else {
                console.error('Request failed with status:', response.status, 'Error:', responseData.error);
                return { success: false, error: responseData.error || 'Request failed' };
            }
        } catch (error) {
            console.error('Authenticated request failed:', error);
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
            console.log('Token value:', token.substring(0, 20) + '...');
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
            
            console.log('Getting auth token from localStorage:', !!token);
            
            if (!token) return null;
            
            // Check if token is expired
            if (expiration && new Date() > new Date(expiration)) {
                console.log('Token expired, clearing...');
                this.clearAuthToken();
                return null;
            }
            
            console.log('Token retrieved successfully');
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

    /**
     * Set up protected route handling
     * Automatically includes JWT token for protected routes
     */
    setupProtectedRouteHandling() {
        console.log('Setting up protected route handling...');
        
        // Check if we're on a protected route
        if (window.location.pathname.startsWith('/user/')) {
            console.log('Currently on protected route, handling...');
            this.handleProtectedRoute();
        }

        // Listen for navigation to protected routes
        window.addEventListener('popstate', (event) => {
            console.log('Popstate event detected:', window.location.pathname);
            if (window.location.pathname.startsWith('/user/')) {
                this.handleProtectedRoute();
            }
        });

        // Intercept all clicks on links to protected routes
        document.addEventListener('click', (e) => {
            if (e.target.tagName === 'A' && e.target.href && e.target.href.includes('/user/')) {
                console.log('Protected route link clicked, intercepting...');
                e.preventDefault();
                const url = e.target.href;
                this.navigateToProtectedRoute(url);
            }
        });

        // Intercept programmatic navigation to protected routes
        const originalPushState = history.pushState;
        history.pushState = function(state, title, url) {
            console.log('PushState called with URL:', url);
            if (url && url.toString().includes('/user/')) {
                // This is a protected route, handle it properly
                console.log('Protected route pushState detected, handling...');
                setTimeout(() => {
                    window.authManager.handleProtectedRoute();
                }, 0);
            }
            return originalPushState.call(this, state, title, url);
        };

        // Handle direct URL access to protected routes
        // This ensures that even if someone types the URL directly, it gets handled
        if (window.location.pathname.startsWith('/user/')) {
            console.log('Direct access to protected route detected, handling...');
            // Small delay to ensure everything is loaded
            setTimeout(() => {
                this.handleProtectedRoute();
            }, 100);
        }
        
        console.log('Protected route handling setup complete');
    }

    /**
     * Navigate to a protected route with proper authentication
     * @param {string} url - The protected route URL
     */
    async navigateToProtectedRoute(url) {
        console.log('navigateToProtectedRoute called with URL:', url);
        const token = this.getAuthToken();
        console.log('Token found in navigateToProtectedRoute:', !!token);
        
        if (!token) {
            // No token, redirect to login
            console.log('No token found, redirecting to login');
            window.location.href = '/auth/login';
            return;
        }

        // Extract the user_id from the URL
        const match = url.match(/\/user\/([^\/]+)/);
        if (!match) {
            console.error('Invalid user profile URL:', url);
            return;
        }

        const user_id = match[1];
        console.log('Extracted user_id:', user_id);
        
        try {
            // Make an authenticated request to get the profile data
            console.log('Making authenticated request to:', `/user/${user_id}`);
            const result = await this.makeAuthenticatedRequest(`/user/${user_id}`);
            console.log('Request result:', result);
            
            if (result.success) {
                // Check if the response is HTML or JSON
                if (typeof result.data === 'string' && result.data.includes('<!DOCTYPE html>')) {
                    // HTML response - replace the page content
                    console.log('HTML response received, replacing page content');
                    document.open();
                    document.write(result.data);
                    document.close();
                } else if (result.data.user) {
                    // JSON response - render the user profile
                    console.log('JSON response received, rendering user profile');
                    this.renderUserProfile(result.data.user);
                } else {
                    // Unexpected response format
                    console.error('Unexpected response format:', result.data);
                    window.location.href = '/auth/login';
                }
                
                // Update browser URL without triggering navigation
                history.pushState({}, '', url);
                console.log('URL updated to:', url);
            } else {
                // Authentication failed, redirect to login
                console.error('Authentication failed:', result.error);
                window.location.href = '/auth/login';
            }
        } catch (error) {
            console.error('Failed to access protected route:', error);
            window.location.href = '/auth/login';
        }
    }

    /**
     * Handle access to protected routes
     */
    async handleProtectedRoute() {
        console.log('handleProtectedRoute called');
        const token = this.getAuthToken();
        console.log('Token found:', !!token);
        
        if (!token) {
            // Redirect to login if no token
            console.log('No token found, redirecting to login');
            window.location.href = '/auth/login';
            return;
        }

        // For protected routes, we need to make an authenticated request
        // to get the page content instead of relying on browser navigation
        const currentPath = window.location.pathname;
        console.log('Protected route accessed with valid token:', currentPath);
        
        try {
            const result = await this.makeAuthenticatedRequest(currentPath);
            if (result.success) {
                // Check if the response is HTML or JSON
                if (typeof result.data === 'string' && result.data.includes('<!DOCTYPE html>')) {
                    // HTML response - replace the page content
                    document.open();
                    document.write(result.data);
                    document.close();
                } else if (result.data.user) {
                    // JSON response - render the user profile
                    this.renderUserProfile(result.data.user);
                } else {
                    // Unexpected response format
                    console.error('Unexpected response format:', result.data);
                    window.location.href = '/auth/login';
                }
            } else {
                // Authentication failed, redirect to login
                console.error('Authentication failed:', result.error);
                window.location.href = '/auth/login';
            }
        } catch (error) {
            console.error('Failed to access protected route:', error);
            window.location.href = '/auth/login';
        }
    }

    /**
     * Render user profile page from JSON data
     * @param {Object} userData - User data from the API
     */
    renderUserProfile(userData) {
        const html = `
            <!DOCTYPE html>
            <html>
            <head>
                <title>User Profile - ${userData.email}</title>
                <style>
                    body { font-family: Arial, sans-serif; margin: 40px; }
                    .profile { max-width: 600px; margin: 0 auto; }
                    .header { background: #f5f5f5; padding: 20px; border-radius: 8px; margin-bottom: 20px; }
                    .info { background: white; padding: 20px; border: 1px solid #ddd; border-radius: 8px; }
                    .logout { background: #dc3545; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px; }
                </style>
            </head>
            <body>
                <div class="profile">
                    <div class="header">
                        <h1>Welcome, ${userData.email}!</h1>
                        <a href="/auth/logout" class="logout">Logout</a>
                    </div>
                    <div class="info">
                        <h2>Your Profile</h2>
                        <p><strong>User ID:</strong> ${userData.user_id}</p>
                        <p><strong>Email:</strong> ${userData.email}</p>
                        <p><strong>Status:</strong> ${userData.status}</p>
                        <p><strong>Member since:</strong> ${userData.created_at}</p>
                    </div>
                </div>
            </body>
            </html>
        `;
        
        document.open();
        document.write(html);
        document.close();
    }
}

// Initialize authentication manager when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    window.authManager = new AuthManager();
});
