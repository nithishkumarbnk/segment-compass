// Auto-dismiss alerts
document.addEventListener("DOMContentLoaded", function () {
  setTimeout(function () {
    let alerts = document.querySelectorAll(".alert");
    alerts.forEach((el) => (el.style.display = "none"));
  }, 4000);
});
