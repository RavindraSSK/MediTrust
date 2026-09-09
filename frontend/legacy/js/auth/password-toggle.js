export function attachPasswordToggle(inputId, toggleBtnId, eyeOpenIconId, eyeClosedIconId) {
  const input = document.getElementById(inputId);
  const btn = document.getElementById(toggleBtnId);
  const eyeOpenIcon = eyeOpenIconId ? document.getElementById(eyeOpenIconId) : null;
  const eyeClosedIcon = eyeClosedIconId ? document.getElementById(eyeClosedIconId) : null;

  if (!input || !btn) return;

  btn.addEventListener("click", () => {
    const isPassword = input.type === "password";
    input.type = isPassword ? "text" : "password";

    if (eyeOpenIcon && eyeClosedIcon) {
      eyeOpenIcon.classList.toggle("hidden-icon", isPassword);
      eyeClosedIcon.classList.toggle("hidden-icon", !isPassword);
    }
  });
}
