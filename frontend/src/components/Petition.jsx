import React, { useState, useEffect } from "react";
import JSONPretty from "react-json-pretty";
import axios from "axios";
import "./css/Petition.css";
import Chart from "./charts/Chart";
import lineChartConfig from "./charts/LineChartConfig";

function Petition({ match }) {
  const petition_id = match.params.petition_id;
  const chartLabel = `Petition ID: ${petition_id}`;
  const [petition, setPetition] = useState({});
  const [latestRecord, setlatestRecord] = useState({});
  const [records, setRecords] = useState(null);
  const [chartTime, setChartTime] = useState({ days: 7 });
  const [chartData, setChartData] = useState([]);
  const [noRecordsFound, setNoRecordsFound] = useState(false);

  useEffect(() => {
    fetchData();
  }, []);

  useEffect(() => {
    generateChartData();
  }, [records]);

  useEffect(() => {
    fetchData();
  }, [chartTime]);

  async function fetchData() {
    const params = { params: { time_ago: chartTime } };
    try {
      let response = await axios.get(`/petition/${petition_id}`, params);
      let data = response["data"];
      setlatestRecord(JSON.parse(data.latest_record));
      setPetition(data.petition);
      setRecords(data.records);
    } catch (error) {
      // handle backend not reachable
      console.log("error:", error);
    }
  }

  function generateChartData() {
    if (records && records.length > 0) {
      let signatureData = records.map((r) => ({
        x: r.timestamp,
        y: r.signatures,
      }));
      setChartData(signatureData);
      setNoRecordsFound(false);
    } else {
      setNoRecordsFound(true);
    }
  }

  const handleChartTimeChange = (event) => {
    event.preventDefault();
    let chartTimeObj = {};

    if (event.target.name === "viewAll") {
      chartTimeObj["all"] = true;
    } else {
      let timeAmount = event.target.amount.value;
      let timeUnit = event.target.units.value;
      chartTimeObj[timeUnit] = parseInt(timeAmount);
    }
    setChartTime(chartTimeObj);
  };

  function dataSinceString() {
    if (chartTime["all"]) {
      return "All Time";
    } else {
      return Object.values(chartTime)[0] + " " + Object.keys(chartTime)[0];
    }
  }

  function hasRecords() {
    return records && records.length > 0;
  }

  return (
    <div className="Petition">
      <h1>Petition ID: {petition_id}</h1>
      <h1>Action: {petition["action"]}</h1>
      <h2>Total signatures: {latestRecord["signatures"]}</h2>

      <div className="PetitionChart">
        <br></br>
        <div className="FetchLatestData">
          <button onClick={fetchData}>Fetch Latest Data!</button>
        </div>
        <br></br>
        <div className="ChangeChartTime">
          <form onSubmit={handleChartTimeChange}>
            <h3>View data since: {hasRecords() ? dataSinceString() : ""}</h3>
            <select name="units">
              <option value="minutes">minutes</option>
              <option value="hours">hours</option>
              <option value="days">days</option>
              <option value="weeks">weeks</option>
            </select>

            <input type="text" name="amount" />
            <input type="submit" value="Submit" />
          </form>
          <button name="viewAll" value="all" onClick={handleChartTimeChange}>
            View All
          </button>
        </div>
        <br></br>
        <div>
          {noRecordsFound
            ? `No records found for last ${dataSinceString()}`
            : ""}
        </div>

        <div className="ChartWrapper">
          <Chart data={chartData} label={chartLabel} />
        </div>

        <br></br>
      </div>

      <div className="data">
        <h2>Petition data:</h2>
        <div>
          <JSONPretty id="json-pretty" data={petition}></JSONPretty>
        </div>

        <h2>Records ({records && records.length}):</h2>
        <div>
          First Record ID:&nbsp;
          {hasRecords() ? records[0]["id"] : "N/A"}
        </div>
        <div>
          <JSONPretty id="json-pretty" data={records}></JSONPretty>
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
