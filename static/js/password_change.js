document.addEventListener('DOMContentLoaded', () => {
    // Admin Change Password
    const adminForm = document.getElementById('adminChangePasswordForm');
    if (adminForm) {
        adminForm.addEventListener('submit', function (e) {
            e.preventDefault();

            const currentPassword = document.getElementById('adminCurrentPassword').value;
            const newPassword = document.getElementById('adminNewPassword').value;
            const confirmPassword = document.getElementById('adminConfirmPassword').value;

            if (newPassword !== confirmPassword) {
                showPopup("New passwords do not match!");
                return;
            }

            fetch('/change_admin_password', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ currentPassword, newPassword })
            })
            .then(res => res.json())
            .then(data => {
                if (data.success) {
                    actionSuccess(data.message || "Password successfully changed!");
                    const modalEl = document.getElementById('adminChangePasswordModal');

                    // Use getInstance for Bootstrap 5, fallback for Bootstrap 4
                    let modal;
                    if (bootstrap.Modal.getOrCreateInstance) {
                        modal = bootstrap.Modal.getOrCreateInstance(modalEl);
                    } else {
                        modal = bootstrap.Modal.getInstance(modalEl);
                    }

                    modal.hide();
                    adminForm.reset();
                } else {
                    showPopup(data.error || "Failed to change password!");
                }
            })
            .catch(err => {
                showPopup("Error updating password: " + err.message);
            });
        });
    }
});

// Popup for errors
function showPopup(message) {
    const alertBox = document.createElement('div');
    alertBox.className = 'alert alert-danger position-fixed top-0 end-0 m-3';
    alertBox.style.zIndex = '9999';
    alertBox.innerText = message;
    document.body.appendChild(alertBox);
    setTimeout(() => alertBox.remove(), 3000);
}

// Popup for success
function actionSuccess(message) {
    const alertBox = document.createElement('div');
    alertBox.className = 'alert alert-success position-fixed top-0 end-0 m-3';
    alertBox.style.zIndex = '9999';
    alertBox.innerText = message;
    document.body.appendChild(alertBox);
    setTimeout(() => alertBox.remove(), 3000);
}