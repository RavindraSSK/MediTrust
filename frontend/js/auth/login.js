const API_BASE = "http://127.0.0.1:8000";

export function initLoginPage() {
  const loginForm = document.getElementById("loginForm");
  const loginBtn = document.getElementById("loginBtn");
  const loginMessage = document.getElementById("loginMessage");
  const togglePassword = document.getElementById("togglePassword");
  const passwordInput = document.getElementById("password");
  const eyeOpenIcon = document.getElementById("eyeOpenIcon");
  const eyeClosedIcon = document.getElementById("eyeClosedIcon");
  const demoBtn = document.querySelector(".explore-demo");

  if (!loginForm || !loginBtn || !passwordInput) return;

  if (togglePassword) {
    togglePassword.addEventListener("click", () => {
      const isPassword = passwordInput.type === "password";
      passwordInput.type = isPassword ? "text" : "password";

      if (eyeOpenIcon && eyeClosedIcon) {
        eyeOpenIcon.classList.toggle("hidden-icon", isPassword);
        eyeClosedIcon.classList.toggle("hidden-icon", !isPassword);
      }
    });
  }

  if (demoBtn) {
    demoBtn.addEventListener("click", () => {
      window.location.href = "demo-coming-soon.html";
    });
  }

  loginForm.addEventListener("submit", async (e) => {
    e.preventDefault();
    if (loginMessage) loginMessage.textContent = "";

    const email = document.getElementById("email")?.value.trim();
    const password = passwordInput.value.trim();

    if (!email || !password) {
      if (loginMessage) {
        loginMessage.textContent = "Please enter your work email and password.";
      }
      return;
    }

    loginBtn.disabled = true;
    loginBtn.textContent = "Signing In...";

    try {
      const response = await fetch(`${API_BASE}/auth/login`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json"
        },
        body: JSON.stringify({ email, password })
      });

      const data = await response.json();

      if (!data.ok) {
        if (loginMessage) {
          loginMessage.textContent = data.message || "Invalid email or password.";
        }
        loginBtn.disabled = false;
        loginBtn.textContent = "Sign In";
        return;
      }

      localStorage.setItem("meditrust_user", JSON.stringify(data));

      if (data.role === "Doctor") {
        window.location.href = "doctor-dashboard.html";
      } else if (data.role === "Nurse") {
        window.location.href = "nurse-dashboard.html";
      } else if (data.role === "Admin") {
        window.location.href = "admin-dashboard.html";
      } else {
        window.location.href = "meditrust.html";
      }
    } catch (error) {
      if (loginMessage) {
        loginMessage.textContent = "Unable to connect to the server. Please try again.";
      }
      loginBtn.disabled = false;
      loginBtn.textContent = "Sign In";
    }
  });
}