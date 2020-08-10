import React, { useState, useEffect } from "react";
import JSONPretty from "react-json-pretty";
import axios from "axios";
import "./css/Petition.css";
import Chart from "./charts/Chart";
import lineChartConfig from "./charts/LineChartConfig";

// const lineData = [
//   {
//     timestamp: new Date(2020, 1, 1, 12),
//     y: 100,
//   },
//   {
//     timestamp: new Date(2020, 1, 2, 12),
//     y: 200,
//   },
//   {
//     timestamp: new Date(2020, 1, 3, 12),
//     y: 400,
//   },
//   {
//     timestamp: new Date(2020, 1, 4, 12),
//     y: 400,
//   },
//   {
//     timestamp: new Date(2020, 1, 5, 12),
//     y: 1200,
//   },
// ];

// const signatures = [100, 200, 400, 400, 1200];
// const timestamps = [
//   new Date(2020, 1, 1, 12),
//   new Date(2020, 1, 2, 12),
//   new Date(2020, 1, 3, 12),
//   new Date(2020, 1, 4, 12),
//   new Date(2020, 1, 5, 12),
// ];

function Petition({ match }) {
  const petition_id = match.params.petition_id;
  const [petition, setPetition] = useState({});
  const [latestRecord, setlatestRecord] = useState({});
  const [latestRecords, setLatestRecords] = useState([]);
  const [chartData, setChartData] = useState([]);
  const [chartLabels, setChartLabels] = useState([]);

  useEffect(() => {
    fetchPetition();
  }, []);

  useEffect(() => {
    generateChartData();
  }, [latestRecords]);

  async function fetchPetition() {
    try {
      let response = await axios.get(`/petition/${petition_id}`);
      let data = response["data"];
      setlatestRecord(JSON.parse(data.latest_record));
      setPetition(data.petition);
      setLatestRecords(data.records);
    } catch (error) {
      // handle application not reachable
      console.log("error:", error);
    }
  }

  function generateChartData() {
    if (latestRecords.length > 0) {
      const timestampLabels = latestRecords.map((r) => new Date(r.timestamp));
      const signatureData = latestRecords.map((r) => ({
        timestamp: new Date(r.timestamp),
        y: r.signatures,
      }));
      setChartLabels(timestampLabels);
      setChartData(signatureData);
    }
  }

  return (
    <div className="Petition">
      <h1>Petition ID: {petition_id}</h1>
      <h1>Action: {petition["action"]}</h1>

      <div className="PetitionChart">
        <h2>Total signatures: {latestRecord["signatures"]}</h2>
        <div className="UpdateChart">
          <button onClick={fetchPetition}>Fetch Latest Data!</button>
        </div>
        <div className="ChartWrapper">
          <Chart chartData={chartData} chartLabels={chartLabels} />
        </div>
      </div>

      <div className="data">
        <h2>Petition data:</h2>
        <div>
          <JSONPretty id="json-pretty" data={petition}></JSONPretty>
        </div>

        <h2>Latest Records ({latestRecords.length}):</h2>
        <div>
          First Record ID:&nbsp;
          {latestRecords.length > 0 ? latestRecords[0]["id"] : "N/A"}
        </div>
        <div>
          <JSONPretty id="json-pretty" data={latestRecords}></JSONPretty>
        </div>

        <h2>Lastest Record:</h2>
        <div>
          <JSONPretty id="json-pretty" data={latestRecord}></JSONPretty>
        </div>
      </div>
    </div>
  );
}

export default Petition;
