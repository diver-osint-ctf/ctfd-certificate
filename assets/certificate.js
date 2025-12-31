document.addEventListener('DOMContentLoaded', () => {
    // Only run on team pages
    if (!location.pathname.startsWith('/team')) {
        return;
    }

    const captainMenu = document.querySelector('div[x-data="CaptainMenu"]');
    const teamHeader = document.querySelector('h1#team-id');
    
    // Target container: CaptainMenu (preferred) or append after Team Header
    let targetContainer = captainMenu;
    
    if (!targetContainer && teamHeader) {
        // Fallback: Create a container if CaptainMenu doesn't exist
        const container = document.createElement('div');
        container.style.marginTop = '10px';
        teamHeader.parentElement.appendChild(container);
        targetContainer = container;
    }

    if (targetContainer) {
        const btnLink = document.createElement('a');
        btnLink.className = 'generate-certificate text-white certificate-tooltip';
        btnLink.id = 'generate-certificate-link';
        btnLink.style.cursor = 'pointer';

        const icon = document.createElement('i');
        icon.className = 'cursor-pointer fas fa-certificate fa-2x px-2 pt-3';

        // Create custom tooltip that matches Bootstrap's style exactly
        const tooltipText = document.createElement('span');
        tooltipText.className = 'tooltip-inner';
        tooltipText.textContent = 'Generate Certificate';

        btnLink.appendChild(icon);
        btnLink.appendChild(tooltipText);
        targetContainer.appendChild(btnLink);

        btnLink.addEventListener('click', function(e) {
            e.preventDefault();
            
            // UI Feedback
            this.style.pointerEvents = 'none';
            icon.className = 'fas fa-spinner fa-spin fa-2x px-2 pt-3';
            
            const formData = new FormData();
            formData.append('nonce', window.init.csrfNonce);
            
            fetch('/certificates/generate', {
                method: 'POST',
                body: formData,
                credentials: 'same-origin'
            })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    window.open(data.view_url, '_blank');
                } else {
                    alert('Error: ' + (data.error || 'Failed to generate certificate'));
                }
            })
            .catch(error => {
                console.error('Error:', error);
                alert('Failed to generate certificate');
            })
            .finally(() => {
                // Reset UI
                this.style.pointerEvents = 'auto';
                icon.className = 'cursor-pointer fas fa-certificate fa-2x px-2 pt-3';
                // Re-init tooltip? Usually not needed if element stayed.
            });
        });
    }
});
