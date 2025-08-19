document.addEventListener("DOMContentLoaded", function () {
    // Function to get the current month details
    function getDaysInMonth() {
        const now = new Date();
        const year = now.getFullYear();
        const month = now.getMonth() + 1; // Months are 0-based in JavaScript

        // Total days in the current month
        const totalDays = new Date(year, month, 0).getDate();

        // Today's date
        const today = now.getDate();

        // Calculate elapsed and remaining days
        const elapsedDays = today;
        const remainingDays = totalDays - today;

        return {
            monthName: now.toLocaleString('default', { month: 'long' }),
            elapsedDays,
            remainingDays
        };
    }

    // Get data for the chart
    const { monthName, elapsedDays, remainingDays } = getDaysInMonth();

    // Render the Doughnut Chart
    const ctx = document.getElementById("doughnut-chart").getContext("2d");
    new Chart(ctx, {
        type: 'doughnut',
        data: {
            labels: ["Elapsed Days", "Remaining Days"],
            datasets: [{
                label: `Days in ${monthName}`,
                data: [elapsedDays, remainingDays],
                backgroundColor: ['#009cff', '#FFFFFF'],
                borderWidth: 1
            }]
        },
        options: {
            responsive: true,
            plugins: {
                legend: {
                    position: 'top'
                },
                title: {
                    display: true,
                    text: `Days in ${monthName}`
                }
            }
        }
    });
});
// Fetch employee count from the server
    fetch('/employee_count')
        .then(response => response.json())
        .then(data => {
            // Update the employee count in the HTML
            document.getElementById('employee-count').innerText = data.count;
        })
        .catch(error => {
            console.error('Error fetching employee count:', error);
            document.getElementById('employee-count').innerText = 'Error';
        });
    function searchEmployee() {
                    // Get the search input and table
                    var input = document.getElementById("search").value.toUpperCase();
                    var table = document.getElementById("table");
                    var rows = table.getElementsByTagName("tr");

                    // Loop through all table rows and hide those who don't match the search
                    for (var i = 1; i < rows.length; i++) {
                        var firstCell = rows[i].getElementsByTagName("td")[0]; // Employee ID (first column)
                        if (firstCell) {
                            var id = firstCell.textContent || firstCell.innerText;
                            if (id.toUpperCase().indexOf(input) > -1) {
                                rows[i].style.display = "";
                            } else {
                                rows[i].style.display = "none";
                            }
                        }
                    }
                }
                document.querySelector('.form-control[type="search"]').addEventListener('input', function () {
                const input = this.value.toUpperCase(); // Get the search input and convert it to uppercase
                const table = document.getElementById('claimsTable'); // Get the table by its ID
                const rows = table.querySelectorAll('tbody tr'); // Get all the rows in the table body

                // Loop through all table rows and check the ClaimID column
                rows.forEach(row => {
                    const claimIDCell = row.querySelector('td'); // Get the first cell (ClaimID)
                    if (claimIDCell) {
                        const claimID = claimIDCell.textContent || claimIDCell.innerText;
                        // Compare input with ClaimID
                        if (claimID.toUpperCase().indexOf(input) > -1) {
                            row.style.display = ''; // Show the row if it matches
                        } else {
                            row.style.display = 'none'; // Hide the row if it doesn't match
                        }
                    }
                });
            });
     document.querySelector('.form-control[type="search"]').addEventListener('input', function () {
    const input = this.value.toUpperCase(); // Get the search input and convert it to uppercase
    const table = document.getElementById('claimsTable'); // Get the table by its ID
    const rows = table.querySelectorAll('tbody tr'); // Get all the rows in the table body

    // Loop through all table rows and check the ClaimID column
    rows.forEach(row => {
        const claimIDCell = row.querySelector('td'); // Get the first cell (ClaimID)
        if (claimIDCell) {
            const claimID = claimIDCell.textContent || claimIDCell.innerText;
            // Compare input with ClaimID
            if (claimID.toUpperCase().indexOf(input) > -1) {
                row.style.display = ''; // Show the row if it matches
            } else {
                row.style.display = 'none'; // Hide the row if it doesn't match
            }
        }
    });
});
     document.querySelector('.form-control[type="search"]').addEventListener('input', function () {
    const input = this.value.toUpperCase(); // Get the search input and convert it to uppercase
    const table = document.getElementById('claimsTable'); // Get the table by its ID
    const rows = table.querySelectorAll('tbody tr'); // Get all the rows in the table body

    // Loop through all table rows and check the ClaimID column
    rows.forEach(row => {
        const claimIDCell = row.querySelector('td'); // Get the first cell (ClaimID)
        if (claimIDCell) {
            const claimID = claimIDCell.textContent || claimIDCell.innerText;
            // Compare input with ClaimID
            if (claimID.toUpperCase().indexOf(input) > -1) {
                row.style.display = ''; // Show the row if it matches
            } else {
                row.style.display = 'none'; // Hide the row if it doesn't match
            }
        }
    });
});

        function toggleCommentField(select, claimId) {
            const commentSection = document.getElementById(`comment-section-${claimId}`);
            if (select.value === 'Approved' || select.value === 'Rejected') {
                commentSection.style.display = 'block';
            } else {
                commentSection.style.display = 'none';
            }
        }
        function showMoreDetails(claimId) {
    // Example data: Replace with a backend API call to fetch claim images
    const claimImages = {
        'claim1': ['../static/img/image1.jpg', '../static/img/image2.jpg'],
        'claim2': ['../static/img/image3.jpg', '../static/img/image4.jpg']
    };

    // Get the images for the selected claim
    const images = claimImages[claimId] || [];
    const carouselImages = document.getElementById('carouselImages');
    carouselImages.innerHTML = ''; // Clear existing images

    if (images.length > 0) {
        images.forEach((image, index) => {
            const activeClass = index === 0 ? 'active' : '';
            carouselImages.innerHTML += `
                <div class="carousel-item ${activeClass}">
                    <img src="${image}" class="d-block w-100" alt="Claim Image">
                </div>
            `;
        });
    } else {
        carouselImages.innerHTML = `
            <div class="carousel-item active">
                <p class="text-center">No images available for this claim.</p>
            </div>
        `;
    }

    // Show the modal
    const modal = new bootstrap.Modal(document.getElementById('moreDetailsModal'));
    modal.show();
}

document.addEventListener("DOMContentLoaded", function () {
    const form = document.querySelector("form");

    form.addEventListener("submit", function (event) {
        let valid = true;

        // Email Validation
        const email = document.getElementById("email");
        const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
        if (!emailRegex.test(email.value)) {
            alert("Please enter a valid email address.");
            valid = false;
        }

        // Password Validation (Minimum 6 characters, at least one number and one special character)
        const password = document.getElementById("password");
        const passwordRegex = /^(?=.*[0-9])(?=.*[!@#$%^&*])[A-Za-z0-9!@#$%^&*]{6,}$/;
        if (!passwordRegex.test(password.value)) {
            alert("Password must be at least 6 characters long and include at least one number and one special character.");
            valid = false;
        }

        // NIC Validation (Assuming Sri Lankan NIC format: 9 or 12 digits with optional ‘V’ or ‘X’ at the end)
        const nic = document.getElementById("nic");
        const nicRegex = /^\d{9}[VXvx]?$|^\d{12}$/;
        if (!nicRegex.test(nic.value)) {
            alert("Please enter a valid NIC number.");
            valid = false;
        }

        // Telephone Number Validation (Only digits, 10 characters long)
        const telephone = document.getElementById("telephone");
        const phoneRegex = /^\d{10}$/;
        if (!phoneRegex.test(telephone.value)) {
            alert("Please enter a valid 10-digit telephone number.");
            valid = false;
        }

        // Gender Selection Validation
        const gender = document.getElementById("gender");
        if (gender.value === "Choose...") {
            alert("Please select a valid gender.");
            valid = false;
        }

        // SBU Selection Validation
        const sbu = document.getElementById("sbu");
        if (sbu.value === "Choose...") {
            alert("Please select a valid SBU.");
            valid = false;
        }

        // Credit Limits (Must be positive if entered)
        const opdCredit = document.getElementById("opd_credit_limit");
        const fuelCredit = document.getElementById("fuel_credit_limit");
        if (opdCredit.value && opdCredit.value < 0) {
            alert("OPD Credit Limit cannot be negative.");
            valid = false;
        }
        if (fuelCredit.value && fuelCredit.value < 0) {
            alert("Fuel Credit Limit cannot be negative.");
            valid = false;
        }

        // Prevent form submission if any validation fails
        if (!valid) {
            event.preventDefault();
        }
    });
});
