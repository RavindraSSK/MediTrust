import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";

import { registerUser } from "../api/endpoints.js";
import AuthShell from "../components/AuthShell.jsx";
import FormMessage from "../components/FormMessage.jsx";
import PasswordField from "../components/PasswordField.jsx";
import PasswordRulesList from "../components/PasswordRulesList.jsx";
import { errorMessage } from "../lib/format.js";
import { getPasswordValidationMessage, isPasswordValid } from "../lib/passwordRules.js";

const INITIAL = { firstName: "", lastName: "", email: "", role: "", hospitalName: "", password: "", confirmPassword: "" };

export default function SignupPage() {
  const navigate = useNavigate();
  const [form, setForm] = useState(INITIAL);
  const [message, setMessage] = useState("");
  const [busy, setBusy] = useState(false);

  const update = (key) => (event) => setForm((current) => ({ ...current, [key]: event.target.value }));

  const handleSubmit = async (event) => {
    event.preventDefault();
    setMessage("");
    const { firstName, lastName, email, role, hospitalName, password, confirmPassword } = form;
    if (!firstName.trim() || !lastName.trim() || !email.trim() || !role || !password || !confirmPassword) {
      setMessage("Please complete all required fields.");
      return;
    }
    if (!isPasswordValid(password)) {
      setMessage(getPasswordValidationMessage(password));
      return;
    }
    if (password !== confirmPassword) {
      setMessage("Passwords do not match.");
      return;
    }
    setBusy(true);
    try {
      const data = await registerUser({
        first_name: firstName.trim(),
        last_name: lastName.trim(),
        email: email.trim(),
        password,
        role,
        hospital_name: hospitalName.trim(),
      });
      if (!data.ok) {
        setMessage(data.message || "Registration failed.");
        return;
      }
      window.alert(data.message || "Account created successfully. Please log in.");
      navigate("/", { replace: true });
    } catch (error) {
      setMessage(error?.status ? errorMessage(error) : "Unable to connect to the server. Please try again.");
    } finally {
      setBusy(false);
    }
  };

  return (
    <AuthShell title="Create Clinician Account" subtitle="Register as authorized healthcare personnel to access MediTrust.">
      <form id="signupForm" className="login-form" noValidate onSubmit={handleSubmit}>
        <div className="field">
          <label htmlFor="firstName">First Name</label>
          <div className="input-wrap">
            <input type="text" id="firstName" placeholder="Enter your first name" value={form.firstName} onChange={update("firstName")} required />
          </div>
        </div>
        <div className="field">
          <label htmlFor="lastName">Last Name</label>
          <div className="input-wrap">
            <input type="text" id="lastName" placeholder="Enter your last name" value={form.lastName} onChange={update("lastName")} required />
          </div>
        </div>
        <div className="field">
          <label htmlFor="email">Work Email</label>
          <div className="input-wrap">
            <input type="email" id="email" placeholder="Enter your work email" value={form.email} onChange={update("email")} autoComplete="username" required />
          </div>
        </div>
        <div className="field">
          <label htmlFor="role">Role</label>
          <div className="input-wrap">
            <select id="role" className="role-select" value={form.role} onChange={update("role")} required>
              <option value="">Select role</option>
              <option value="Doctor">Doctor</option>
              <option value="Nurse">Nurse</option>
              <option value="Admin">Admin</option>
            </select>
          </div>
        </div>
        <div className="field">
          <label htmlFor="hospitalName">Hospital / Clinic Name</label>
          <div className="input-wrap">
            <input type="text" id="hospitalName" placeholder="Enter hospital or clinic name" value={form.hospitalName} onChange={update("hospitalName")} />
          </div>
        </div>

        <PasswordField id="password" label="Password" placeholder="8 to 12 characters" value={form.password} onChange={(value) => setForm((c) => ({ ...c, password: value }))} autoComplete="new-password">
          <PasswordRulesList password={form.password} />
        </PasswordField>
        <PasswordField id="confirmPassword" label="Confirm Password" placeholder="Re-enter your password" value={form.confirmPassword} onChange={(value) => setForm((c) => ({ ...c, confirmPassword: value }))} autoComplete="new-password" />

        <FormMessage id="signupMessage" text={message} />

        <button type="submit" className="signin-btn" disabled={busy}>
          {busy ? "Creating Account..." : "Create Account"}
        </button>
      </form>

      <div className="section-line" />
      <div className="secondary-row">
        <p>
          Already have an account?{" "}
          <Link to="/" className="text-link strong-link">
            Login
          </Link>
        </p>
      </div>
    </AuthShell>
  );
}
