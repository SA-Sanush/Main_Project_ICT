const fileInput = document.querySelector("#resume_file");
const form = document.querySelector("#resume-form");

if (fileInput) {
  fileInput.addEventListener("change", (event) => {
    const fileName = event.target.files[0]?.name || "Choose a file";
    const label = event.target.closest(".file-label");
    if (label) {
      label.querySelector("span").textContent = fileName;
    }
  });
}

if (form) {
  form.addEventListener("submit", () => {
    const button = form.querySelector('button[type="submit"]');
    if (button) {
      button.textContent = "Scanning…";
      button.disabled = true;
    }
  });
}
