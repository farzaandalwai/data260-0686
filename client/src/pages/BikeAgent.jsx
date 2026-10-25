import { useState } from "react";
import api, { errorMessage } from "../api/axios";

function BikeAgent() {
  const [file, setFile] = useState(null);
  const [url, setUrl] = useState("https://divvybikes.com/pricing");
  const [output, setOutput] = useState(null);
  const [error, setError] = useState("");
  const [running, setRunning] = useState(false);

  async function run(event) {
    event.preventDefault();
    setError("");
    setOutput(null);
    setRunning(true);
    try {
      const form = new FormData();
      form.append("csv_file", file);
      form.append("pricing_url", url);
      const response = await api.post("/api/hw7/bike/analyze", form);
      setOutput(response.data);
    } catch (failure) {
      setError(errorMessage(failure));
    } finally {
      setRunning(false);
    }
  }

  return (
    <section className="card">
      <h1>Divvy bike-share agent</h1>
      <p>Upload a Divvy scenario CSV. The selected rides are modeled from real anonymized trips.</p>
      <form onSubmit={run}>
        <div className="field"><label htmlFor="bike-csv">Trip CSV</label><input id="bike-csv" type="file" accept=".csv" onChange={(event) => setFile(event.target.files[0])} required /></div>
        <div className="field"><label htmlFor="pricing-url">Official pricing URL</label><input id="pricing-url" type="url" value={url} onChange={(event) => setUrl(event.target.value)} required /></div>
        <button className="btn primary" type="submit" disabled={running}>{running ? "Running..." : "Run"}</button>
      </form>
      {error ? <p className="error">{error}</p> : null}
      {output ? <div>
        <h2>{output.result?.decision || output.stop_reason}</h2>
        {output.result ? <>
          <p>{output.result.rationale}</p>
          <p>CSV rows: {output.result.total_csv_rows}; modeled rides: {output.result.scenario_rides}; pay-per-use year: ${output.result.annualized_pay_per_use}; annual membership upfront: ${output.result.annual_membership_billed_upfront} (${output.result.monthly_equivalent_membership}/month equivalent, ${output.result.membership_residual_charges} residual); break-even rides/year: {output.result.break_even_rides_per_year}; break-even average minutes at this frequency: {output.result.break_even_average_minutes_at_actual_frequency}.</p>
          <p>Pricing source: <a href={output.result.pricing_url}>{output.result.pricing_url}</a>; captured {output.result.pricing_capture_utc}; SHA-256 {output.result.pricing_sha256}.</p>
          <h3>Weekly rides, average minutes, spend</h3>
          <ul>{output.result.weekly.map((week) => <li key={week.week}>Week {week.week}: {week.rides} rides, {week.avg_minutes} min, ${week.pay_cost}</li>)}</ul>
        </> : null}
        <p>Steps: {output.steps}; time: {output.time_ms} ms; stop: {output.stop_reason}</p>
        <h3>Tool timeline</h3>
        <ol>{output.timeline.map((step, index) => <li key={index}><strong>{step.tool}</strong><pre>{JSON.stringify(step.inputs, null, 2)}</pre><pre>{JSON.stringify(step.observation, null, 2)}</pre></li>)}</ol>
      </div> : null}
    </section>
  );
}

export default BikeAgent;
