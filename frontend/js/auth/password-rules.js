export function getPasswordValidation(password) {
  return {
    minLength: password.length >= 8,
    hasUpper: /[A-Z]/.test(password),
    hasLower: /[a-z]/.test(password),
    hasNumber: /\d/.test(password),
    hasSpecial: /[^A-Za-z0-9]/.test(password),
  };
}

export function renderPasswordRules(container, password) {
  if (!container) return;

  const rules = getPasswordValidation(password);

  const items = [
    { label: "At least 8 characters", ok: rules.minLength },
    { label: "At least one uppercase letter", ok: rules.hasUpper },
    { label: "At least one lowercase letter", ok: rules.hasLower },
    { label: "At least one number", ok: rules.hasNumber },
    { label: "At least one special character", ok: rules.hasSpecial },
  ];

  container.innerHTML = `
    <ul class="rules-list">
      ${items.map(item => `
        <li class="${item.ok ? "rule-ok" : "rule-pending"}">
          ${item.label}
        </li>
      `).join("")}
    </ul>
  `;
}