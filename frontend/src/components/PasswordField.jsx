import { useState } from "react";

function EyeOpen() {
  return (
    <svg viewBox="0 0 24 24" fill="none" aria-hidden="true">
      <path d="M2 12C4.2 7.8 7.8 5 12 5C16.2 5 19.8 7.8 22 12C19.8 16.2 16.2 19 12 19C7.8 19 4.2 16.2 2 12Z" stroke="currentColor" strokeWidth="1.8" strokeLinejoin="round" />
      <circle cx="12" cy="12" r="3" stroke="currentColor" strokeWidth="1.8" />
    </svg>
  );
}

function EyeClosed() {
  return (
    <svg viewBox="0 0 24 24" fill="none" aria-hidden="true">
      <path d="M3 3L21 21" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" />
      <path d="M10.6 6.3C11.06 6.1 11.53 6 12 6C16.2 6 19.8 8.8 22 13C21.15 14.62 20.05 15.95 18.74 16.93" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" />
      <path d="M14.12 14.12C13.58 14.66 12.82 15 12 15C10.34 15 9 13.66 9 12C9 11.18 9.34 10.42 9.88 9.88" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" />
      <path d="M6.06 9.26C4.75 10.23 3.66 11.52 2.82 13C5.02 17.2 8.4 20 12 20C13.96 20 15.81 19.17 17.38 17.74" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}

function LockIcon() {
  return (
    <span className="input-icon" aria-hidden="true">
      <svg viewBox="0 0 24 24" fill="none">
        <rect x="5" y="10" width="14" height="10" rx="2" stroke="currentColor" strokeWidth="1.8" />
        <path d="M8 10V7.8C8 5.7 9.7 4 12 4C14.3 4 16 5.7 16 7.8V10" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" />
      </svg>
    </span>
  );
}

export default function PasswordField({ id, label, value, onChange, placeholder = "Enter your password", withIcon = false, autoComplete = "current-password", children }) {
  const [visible, setVisible] = useState(false);
  return (
    <div className="field">
      <label htmlFor={id}>{label}</label>
      <div className="input-wrap">
        {withIcon ? <LockIcon /> : null}
        <input
          type={visible ? "text" : "password"}
          id={id}
          name={id}
          value={value}
          onChange={(event) => onChange(event.target.value)}
          placeholder={placeholder}
          autoComplete={autoComplete}
          required
        />
        <button
          type="button"
          className="password-toggle"
          aria-label={visible ? "Hide password" : "Show password"}
          onClick={() => setVisible((current) => !current)}
        >
          {visible ? <EyeClosed /> : <EyeOpen />}
        </button>
      </div>
      {children}
    </div>
  );
}
