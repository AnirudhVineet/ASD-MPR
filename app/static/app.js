// Mobile navigation toggle and dismissible flash messages.
document.addEventListener("click", (event) => {
  const toggle = event.target.closest("[data-nav-toggle]");
  if (toggle) {
    const header = toggle.closest(".site-header");
    const open = header.classList.toggle("nav-open");
    toggle.setAttribute("aria-expanded", String(open));
    return;
  }

  const dismiss = event.target.closest("[data-dismiss]");
  if (dismiss) {
    dismiss.closest(".flash").remove();
  }
});
