// Mobile Menu Toggle
document.addEventListener('DOMContentLoaded', function() {
    const mobileMenuToggle = document.getElementById('mobileMenuToggle');
    const navMenu = document.getElementById('navMenu');
    
    if (mobileMenuToggle) {
        mobileMenuToggle.addEventListener('click', function() {
            navMenu.classList.toggle('active');
            this.classList.toggle('active');
        });
    }
    
    // Smooth scroll for anchor links
    document.querySelectorAll('a[href^="#"]').forEach(anchor => {
        anchor.addEventListener('click', function (e) {
            const href = this.getAttribute('href');
            if (href !== '#' && href.length > 1) {
                e.preventDefault();
                const target = document.querySelector(href);
                if (target) {
                    target.scrollIntoView({
                        behavior: 'smooth',
                        block: 'start'
                    });
                    
                    // Close mobile menu if open
                    if (navMenu.classList.contains('active')) {
                        navMenu.classList.remove('active');
                        mobileMenuToggle.classList.remove('active');
                    }
                }
            }
        });
    });
    
    // Navbar scroll effect
    let lastScroll = 0;
    const navbar = document.querySelector('.navbar');
    
    window.addEventListener('scroll', function() {
        const currentScroll = window.pageYOffset;
        
        if (currentScroll <= 0) {
            navbar.style.boxShadow = 'none';
        } else {
            navbar.style.boxShadow = '0 2px 4px rgba(0, 0, 0, 0.05)';
        }
        
        lastScroll = currentScroll;
    });
    
    // Animated numbers counter (for stats)
    function animateValue(element, start, end, duration) {
        let startTimestamp = null;
        const step = (timestamp) => {
            if (!startTimestamp) startTimestamp = timestamp;
            const progress = Math.min((timestamp - startTimestamp) / duration, 1);
            
            const value = Math.floor(progress * (end - start) + start);
            
            // Format numbers with K, M, B
            let displayValue;
            if (end >= 1000000000) {
                displayValue = (value / 1000000000).toFixed(1) + 'B';
            } else if (end >= 1000000) {
                displayValue = (value / 1000000).toFixed(1) + 'M';
            } else if (end >= 1000) {
                displayValue = (value / 1000).toFixed(1) + 'K';
            } else {
                displayValue = value;
            }
            
            // Special handling for percentage
            if (element.textContent.includes('%')) {
                displayValue += '%';
            }
            
            element.textContent = displayValue;
            
            if (progress < 1) {
                window.requestAnimationFrame(step);
            } else {
                // Set final value
                if (element.dataset.finalValue) {
                    element.textContent = element.dataset.finalValue;
                }
            }
        };
        window.requestAnimationFrame(step);
    }
    
    // Intersection Observer for animation triggers
    const observerOptions = {
        threshold: 0.3,
        rootMargin: '0px 0px -100px 0px'
    };
    
    const observer = new IntersectionObserver((entries) => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                entry.target.classList.add('animate-in');
                
                // Animate stat numbers
                if (entry.target.classList.contains('stat-value')) {
                    const text = entry.target.textContent;
                    const numMatch = text.match(/[\d.]+/);
                    if (numMatch) {
                        const num = parseFloat(numMatch[0]);
                        entry.target.dataset.finalValue = text;
                        
                        // Convert to actual number for animation
                        let actualNum = num;
                        if (text.includes('K')) actualNum *= 1000;
                        if (text.includes('M')) actualNum *= 1000000;
                        if (text.includes('B')) actualNum *= 1000000000;
                        
                        animateValue(entry.target, 0, actualNum, 2000);
                    }
                }
                
                observer.unobserve(entry.target);
            }
        });
    }, observerOptions);
    
    // Observe elements for animation
    document.querySelectorAll('.feature-card, .stat-value, .stats-card').forEach(el => {
        observer.observe(el);
    });
    
    // Add fade-in animation on scroll
    const fadeElements = document.querySelectorAll('.hero-text, .hero-visual, .section-header');
    fadeElements.forEach(el => {
        el.style.opacity = '0';
        el.style.transform = 'translateY(20px)';
        el.style.transition = 'opacity 0.6s ease, transform 0.6s ease';
    });
    
    setTimeout(() => {
        fadeElements.forEach((el, index) => {
            setTimeout(() => {
                el.style.opacity = '1';
                el.style.transform = 'translateY(0)';
            }, index * 100);
        });
    }, 100);
});

// Add active class styles via JavaScript if needed
const style = document.createElement('style');
style.textContent = `
    @media (max-width: 768px) {
        .nav-menu.active {
            display: flex;
            flex-direction: column;
            position: absolute;
            top: 72px;
            left: 0;
            right: 0;
            background: white;
            padding: 24px;
            border-bottom: 1px solid var(--border-color);
            box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
        }
        
        .mobile-menu-toggle.active span:nth-child(1) {
            transform: rotate(45deg) translate(5px, 5px);
        }
        
        .mobile-menu-toggle.active span:nth-child(2) {
            opacity: 0;
        }
        
        .mobile-menu-toggle.active span:nth-child(3) {
            transform: rotate(-45deg) translate(7px, -7px);
        }
    }
    
    .animate-in {
        animation: fadeInUp 0.6s ease forwards;
    }
    
    @keyframes fadeInUp {
        from {
            opacity: 0;
            transform: translateY(30px);
        }
        to {
            opacity: 1;
            transform: translateY(0);
        }
    }
`;
document.head.appendChild(style);
