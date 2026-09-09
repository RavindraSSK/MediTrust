import { useAuth } from "../auth/AuthContext.jsx";
import DashboardShell from "../components/DashboardShell.jsx";
import ModelCard from "../components/ModelCard.jsx";

export default function ModelCardPage() {
  const { displayName, dashboardPath } = useAuth();
  return (
    <DashboardShell
      title="Model Card"
      subtitle="How the cardiovascular risk model was built, benchmarked and calibrated, plus the curated evidence sources"
      userLabel={displayName || "Clinician"}
      links={[
        { to: dashboardPath, label: "Back to Dashboard" },
        { to: "/assessment", label: "New Assessment" },
      ]}
    >
      <section className="panel-box wide-panel">
        <div className="clinical-panel-header">
          <div>
            <h2>Cardiovascular risk model</h2>
            <p>
              Selected by cross-validated ROC-AUC from a Logistic Regression / Random Forest / XGBoost benchmark with
              hyperparameter search. Triage bands come from clinically oriented threshold optimisation (sensitivity floor
              for rule-out, specificity floor for rule-in). SHAP explains every prediction in probability space.
            </p>
          </div>
        </div>
        <ModelCard />
      </section>
    </DashboardShell>
  );
}
