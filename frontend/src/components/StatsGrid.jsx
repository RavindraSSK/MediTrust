export default function StatsGrid({ stats }) {
  return (
    <section className="stats-grid">
      {stats.map((stat) => (
        <div className="stat-box" key={stat.label}>
          <h3>{stat.label}</h3>
          <p id={stat.id}>{stat.value ?? 0}</p>
        </div>
      ))}
    </section>
  );
}
