/**
 * TokenGuard - Common JavaScript Utilities
 * 
 * This file contains reusable JavaScript functions and utilities that are used
 * across multiple pages in the application. It provides a centralized location
 * for common functionality, reducing code duplication and improving maintainability.
 * 
 * Features:
 * - Form validation utilities
 * - Message display system
 * - Loading state management
 * - Common DOM manipulation helpers
 * - Error handling utilities
 */

// ============================================================================
// Constants and Configuration
// ============================================================================

/**
 * Application configuration constants
 * These values can be easily modified in one place
 */
const APP_CONFIG = {
    // Animation durations in milliseconds
    ANIMATION_DURATION: 300,
    
    // Message display duration in milliseconds
    MESSAGE_DISPLAY_DURATION: 5000,
    
    // API endpoints (can be overridden by server-side variables)
    API_ENDPOINTS: {
        REGISTER: '/auth/register',
        LOGIN: '/auth/login',
        FORGOT_PASSWORD: '/auth/forgot-password',
        RESET_PASSWORD: '/auth/reset-password'
    },
    
    // Validation patterns
    VALIDATION_PATTERNS: {
        EMAIL: /^[^\s@]+@[^\s@]+\.[^\s@]+$/,
        PASSWORD_MIN_LENGTH: 8
    }
};

// ============================================================================
// Utility Functions
// ============================================================================

/**
 * Debounce function to limit how often a function can be called
 * Useful for input validation and search functionality
 * 
 * @param {Function} func - The function to debounce
 * @param {number} wait - The delay in milliseconds
 * @returns {Function} - Debounced function
 */
function debounce(func, wait) {
    let timeout;
    return function executedFunction(...args) {
        const later = () => {
            clearTimeout(timeout);
            func(...args);
        };
        clearTimeout(timeout);
        timeout = setTimeout(later, wait);
    };
}

/**
 * Throttle function to limit function execution rate
 * Useful for scroll events and other frequent events
 * 
 * @param {Function} func - The function to throttle
 * @param {number} limit - The time limit in milliseconds
 * @returns {Function} - Throttled function
 */
function throttle(func, limit) {
    let inThrottle;
    return function() {
        const args = arguments;
        const context = this;
        if (!inThrottle) {
            func.apply(context, args);
            inThrottle = true;
            setTimeout(() => inThrottle = false, limit);
        }
    };
}

/**
 * Generate a unique ID for DOM elements
 * Useful for creating unique identifiers for dynamically generated content
 * 
 * @returns {string} - Unique ID string
 */
function generateUniqueId() {
    return 'id_' + Math.random().toString(36).substr(2, 9);
}

// ============================================================================
// DOM Manipulation Utilities
// ============================================================================

/**
 * Safe DOM element selector with error handling
 * Returns null if element is not found instead of throwing an error
 * 
 * @param {string} selector - CSS selector string
 * @param {Element} parent - Parent element to search within (defaults to document)
 * @returns {Element|null} - Found element or null
 */
function safeQuerySelector(selector, parent = document) {
    try {
        return parent.querySelector(selector);
    } catch (error) {
        console.warn(`Invalid selector: ${selector}`, error);
        return null;
    }
}

/**
 * Safe DOM element selector for multiple elements
 * Returns empty array if no elements found
 * 
 * @param {string} selector - CSS selector string
 * @param {Element} parent - Parent element to search within (defaults to document)
 * @returns {Element[]} - Array of found elements
 */
function safeQuerySelectorAll(selector, parent = document) {
    try {
        return Array.from(parent.querySelectorAll(selector));
    } catch (error) {
        console.warn(`Invalid selector: ${selector}`, error);
        return [];
    }
}

/**
 * Add event listener with error handling
 * Safely adds event listeners and logs any errors
 * 
 * @param {Element} element - Target element
 * @param {string} event - Event type
 * @param {Function} handler - Event handler function
 * @param {Object} options - Event listener options
 */
function safeAddEventListener(element, event, handler, options = {}) {
    if (!element) {
        console.warn('Cannot add event listener: element is null');
        return;
    }
    
    try {
        element.addEventListener(event, handler, options);
    } catch (error) {
        console.error(`Failed to add ${event} event listener:`, error);
    }
}

// ============================================================================
// Form Validation Utilities
// ============================================================================

/**
 * Validate email format using regex pattern
 * 
 * @param {string} email - Email string to validate
 * @returns {boolean} - True if email is valid
 */
function isValidEmail(email) {
    if (!email || typeof email !== 'string') return false;
    return APP_CONFIG.VALIDATION_PATTERNS.EMAIL.test(email.trim());
}

/**
 * Validate password strength
 * Returns an object with validation results and suggestions
 * 
 * @param {string} password - Password string to validate
 * @returns {Object} - Validation result object
 */
function validatePassword(password) {
    if (!password || typeof password !== 'string') {
        return {
            isValid: false,
            strength: 0,
            message: 'Password is required',
            suggestions: []
        };
    }
    
    const suggestions = [];
    let strength = 0;
    
    // Check length
    if (password.length >= APP_CONFIG.VALIDATION_PATTERNS.PASSWORD_MIN_LENGTH) {
        strength++;
    } else {
        suggestions.push(`At least ${APP_CONFIG.VALIDATION_PATTERNS.PASSWORD_MIN_LENGTH} characters`);
    }
    
    // Check for uppercase letters
    if (/[A-Z]/.test(password)) {
        strength++;
    } else {
        suggestions.push('Include uppercase letters');
    }
    
    // Check for lowercase letters
    if (/[a-z]/.test(password)) {
        strength++;
    } else {
        suggestions.push('Include lowercase letters');
    }
    
    // Check for numbers
    if (/\d/.test(password)) {
        strength++;
    } else {
        suggestions.push('Include numbers');
    }
    
    // Check for special characters
    if (/[^A-Za-z0-9]/.test(password)) {
        strength++;
    } else {
        suggestions.push('Include special characters');
    }
    
    // Determine strength level and message
    let message = '';
    if (strength <= 2) {
        message = 'Very Weak';
    } else if (strength === 3) {
        message = 'Weak';
    } else if (strength === 4) {
        message = 'Medium';
    } else {
        message = 'Strong';
    }
    
    return {
        isValid: strength >= 3, // Consider medium strength as valid
        strength,
        message,
        suggestions
    };
}

/**
 * Validate that two password fields match
 * 
 * @param {string} password - First password
 * @param {string} confirmPassword - Confirmation password
 * @returns {Object} - Validation result
 */
function validatePasswordMatch(password, confirmPassword) {
    if (!password || !confirmPassword) {
        return {
            isValid: false,
            message: 'Both passwords are required'
        };
    }
    
    if (password !== confirmPassword) {
        return {
            isValid: false,
            message: 'Passwords do not match'
        };
    }
    
    return {
        isValid: true,
        message: 'Passwords match'
    };
}

// ============================================================================
// Message Display System
// ============================================================================

/**
 * Message display system for showing user feedback
 * Provides consistent styling and behavior across the application
 */
class MessageDisplay {
    constructor() {
        this.messageContainer = null;
        this.messageQueue = [];
        this.isProcessing = false;
        this.init();
    }
    
    /**
     * Initialize the message display system
     * Creates message container if it doesn't exist
     */
    init() {
        // Look for existing message container
        this.messageContainer = document.getElementById('flash-messages');
        
        // Create container if it doesn't exist
        if (!this.messageContainer) {
            this.messageContainer = document.createElement('div');
            this.messageContainer.id = 'flash-messages';
            this.messageContainer.className = 'flash-container';
            document.body.appendChild(this.messageContainer);
        }
    }
    
    /**
     * Show a message to the user
     * 
     * @param {string} message - Message text to display
     * @param {string} type - Message type (success, error, info, warning)
     * @param {number} duration - Display duration in milliseconds
     */
    show(message, type = 'info', duration = APP_CONFIG.MESSAGE_DISPLAY_DURATION) {
        const messageData = { message, type, duration };
        this.messageQueue.push(messageData);
        
        if (!this.isProcessing) {
            this.processQueue();
        }
    }
    
    /**
     * Process the message queue
     * Shows messages one at a time to avoid overwhelming the user
     */
    processQueue() {
        if (this.messageQueue.length === 0) {
            this.isProcessing = false;
            return;
        }
        
        this.isProcessing = true;
        const messageData = this.messageQueue.shift();
        this.displayMessage(messageData);
    }
    
    /**
     * Display a single message
     * 
     * @param {Object} messageData - Message data object
     */
    displayMessage(messageData) {
        const { message, type, duration } = messageData;
        
        // Create message element
        const messageElement = document.createElement('div');
        messageElement.className = `flash-message flash-${type}`;
        messageElement.innerHTML = `
            <span class="flash-text">${this.escapeHtml(message)}</span>
            <button class="flash-close" onclick="this.parentElement.remove()">&times;</button>
        `;
        
        // Add to container
        this.messageContainer.appendChild(messageElement);
        
        // Auto-remove after duration
        setTimeout(() => {
            if (messageElement.parentNode) {
                messageElement.remove();
            }
            
            // Process next message
            setTimeout(() => this.processQueue(), 100);
        }, duration);
    }
    
    /**
     * Escape HTML to prevent XSS attacks
     * 
     * @param {string} text - Text to escape
     * @returns {string} - Escaped text
     */
    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }
    
    /**
     * Clear all messages
     */
    clear() {
        if (this.messageContainer) {
            this.messageContainer.innerHTML = '';
        }
        this.messageQueue = [];
        this.isProcessing = false;
    }
}

// ============================================================================
// Loading State Management
// ============================================================================

/**
 * Loading state manager for buttons and forms
 * Provides consistent loading behavior across the application
 */
class LoadingManager {
    constructor() {
        this.loadingElements = new Map();
    }
    
    /**
     * Set loading state for an element
     * 
     * @param {Element} element - Element to set loading state for
     * @param {boolean} loading - Whether to show loading state
     * @param {string} loadingText - Text to show during loading
     */
    setLoading(element, loading, loadingText = 'Loading...') {
        if (!element) return;
        
        if (loading) {
            this.showLoading(element, loadingText);
        } else {
            this.hideLoading(element);
        }
    }
    
    /**
     * Show loading state for an element
     * 
     * @param {Element} element - Element to show loading state for
     * @param {string} loadingText - Text to show during loading
     */
    showLoading(element, loadingText) {
        // Store original state
        this.loadingElements.set(element, {
            disabled: element.disabled,
            text: element.textContent || element.innerHTML
        });
        
        // Set loading state
        element.disabled = true;
        element.classList.add('loading');
        
        // Update text if loading text is provided
        if (loadingText) {
            const btnText = element.querySelector('.btn-text');
            const btnLoading = element.querySelector('.btn-loading');
            
            if (btnText && btnLoading) {
                btnText.style.display = 'none';
                btnLoading.style.display = 'inline';
                btnLoading.textContent = loadingText;
            }
        }
    }
    
    /**
     * Hide loading state for an element
     * 
     * @param {Element} element - Element to hide loading state for
     */
    hideLoading(element) {
        // Restore original state
        const originalState = this.loadingElements.get(element);
        if (originalState) {
            element.disabled = originalState.disabled;
            element.classList.remove('loading');
            
            // Restore text
            const btnText = element.querySelector('.btn-text');
            const btnLoading = element.querySelector('.btn-loading');
            
            if (btnText && btnLoading) {
                btnText.style.display = 'inline';
                btnLoading.style.display = 'none';
            }
            
            this.loadingElements.delete(element);
        }
    }
}

// ============================================================================
// Error Handling Utilities
// ============================================================================

/**
 * Global error handler for unhandled errors
 * Logs errors and shows user-friendly messages
 */
function setupGlobalErrorHandling() {
    // Handle unhandled promise rejections
    window.addEventListener('unhandledrejection', (event) => {
        console.error('Unhandled promise rejection:', event.reason);
        event.preventDefault();
    });
    
    // Handle JavaScript errors
    window.addEventListener('error', (event) => {
        console.error('JavaScript error:', event.error);
    });
}

/**
 * Safe JSON parsing with error handling
 * 
 * @param {string} jsonString - JSON string to parse
 * @param {*} defaultValue - Default value if parsing fails
 * @returns {*} - Parsed object or default value
 */
function safeJsonParse(jsonString, defaultValue = null) {
    try {
        return JSON.parse(jsonString);
    } catch (error) {
        console.warn('Failed to parse JSON:', error);
        return defaultValue;
    }
}

// ============================================================================
// Initialization
// ============================================================================

/**
 * Initialize common utilities when DOM is ready
 */
document.addEventListener('DOMContentLoaded', () => {
    // Setup global error handling
    setupGlobalErrorHandling();
    
    // Create global instances
    window.messageDisplay = new MessageDisplay();
    window.loadingManager = new LoadingManager();
    
    // Log initialization
    console.log('TokenGuard Common JavaScript initialized');
});

// ============================================================================
// Export for module systems (if needed)
// ============================================================================

// Make utilities available globally for backward compatibility
window.TokenGuard = {
    utils: {
        debounce,
        throttle,
        generateUniqueId,
        safeQuerySelector,
        safeQuerySelectorAll,
        safeAddEventListener,
        isValidEmail,
        validatePassword,
        validatePasswordMatch,
        safeJsonParse
    },
    messageDisplay: null, // Will be set after initialization
    loadingManager: null  // Will be set after initialization
};
