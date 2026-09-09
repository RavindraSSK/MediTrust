export default function FormMessage({ id, text, tone = "", inline = false }) {
  const classes = ["form-message", inline ? "form-message-inline" : "", tone ? `is-${tone}` : ""].filter(Boolean).join(" ");
  return (
    <div id={id} className={classes} aria-live="polite">
      {text || ""}
    </div>
  );
}
