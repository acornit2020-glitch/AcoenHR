document.addEventListener("DOMContentLoaded", function() {
    const sidebar = document.getElementById('sidebarMenu');
    const toggleBtn = document.getElementById('sidebarToggle') || document.querySelector('.sidebar-toggler');

    if (sidebar && toggleBtn) {
        toggleBtn.addEventListener('click', function(e) {
            e.preventDefault();
            e.stopPropagation();
            sidebar.classList.toggle('active');
        });

        document.addEventListener('click', function(e) {
            if (window.innerWidth < 768) {
                if (!sidebar.contains(e.target) && !toggleBtn.contains(e.target)) {
                    sidebar.classList.remove('active');
                }
            }
        });
    }
});