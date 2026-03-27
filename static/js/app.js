// FORMA Pilates - App JS

// Auto-dismiss flash messages
document.addEventListener('DOMContentLoaded', function () {
    setTimeout(function () {
        document.querySelectorAll('[data-flash]').forEach(function (el) {
            el.style.transition = 'opacity 0.5s ease';
            el.style.opacity = '0';
            setTimeout(function () { el.remove(); }, 500);
        });
    }, 4000);

    // Smooth scroll for anchor links
    document.querySelectorAll('a[href^="#"]').forEach(function (anchor) {
        anchor.addEventListener('click', function (e) {
            e.preventDefault();
            var target = document.querySelector(this.getAttribute('href'));
            if (target) target.scrollIntoView({ behavior: 'smooth' });
        });
    });

    // Lazy load images
    if ('IntersectionObserver' in window) {
        var imgObserver = new IntersectionObserver(function (entries) {
            entries.forEach(function (entry) {
                if (entry.isIntersecting) {
                    var img = entry.target;
                    if (img.dataset.src) {
                        img.src = img.dataset.src;
                        imgObserver.unobserve(img);
                    }
                }
            });
        });
        document.querySelectorAll('img[data-src]').forEach(function (img) {
            imgObserver.observe(img);
        });
    }

    // Range slider value display
    document.querySelectorAll('input[type="range"]').forEach(function (slider) {
        var display = document.getElementById(slider.id + '_display');
        if (display) {
            display.textContent = slider.value;
            slider.addEventListener('input', function () {
                display.textContent = this.value;
            });
        }
    });
});

// HTMX: show loading indicator on requests
document.body.addEventListener('htmx:beforeRequest', function (e) {
    var indicator = document.getElementById('htmx-loader');
    if (indicator) indicator.style.display = 'flex';
});
document.body.addEventListener('htmx:afterRequest', function (e) {
    var indicator = document.getElementById('htmx-loader');
    if (indicator) indicator.style.display = 'none';
});

// Confirm dialog helper
function confirmAction(message, formEl) {
    if (confirm(message)) formEl.submit();
}
