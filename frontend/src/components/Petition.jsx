import React, { useState, useEffect } from "react";
import JSONPretty from "react-json-pretty";
import axios from "axios";
import "./css/Petition.css";

import Chart from "./charts/Chart";
// import { lineChartConfig } from "./charts/LineChartConfig";

function Petition({ match }) {
  const petition_id = match.params.petition_id;
  const [petition, setPetition] = useState({});
  const [latestRecord, setlatestRecord] = useState({});
  const [latestRecords, setLatestRecords] = useState({});
  const [chartData, setChartData] = useState([]);

  useEffect(() => {
    fetchPetition();
    fetchData();
  }, []);

  // dummy function for fetching data from the API
  const fetchData = () => {
    const randomInt = () => Math.floor(Math.random() * (10 - 1 + 1)) + 1;
    const data = [
      randomInt(),
      randomInt(),
      randomInt(),
      randomInt(),
      randomInt(),
      randomInt(),
    ];
    setChartData(data);
  };

  async function fetchPetition() {
    try {
      let response = await axios.get(`/petition/${petition_id}`);
      let data = response["data"];
      setPetition(data["petition"]);
      setlatestRecord(data["latest_record"]);
      setLatestRecords(data["records"]);
    } catch (error) {
      // handle application not reachable
      console.log("error:", error);
    }
  }

  return (
    <div className="Petition">
      <h1>Petition ID: {petition_id}</h1>
      <h1>Action: {petition["action"]}</h1>

      <div className="PetitionChart">
        <h2>Total signatures</h2>
        <div className="UpdateChart">
          <button onClick={fetchData}>Fetch Random Data!</button>
        </div>
        <div className="ChartWrapper">
          <Chart chartData={chartData} />
        </div>
      </div>

      <div className="data">
        <h2>Petition data:</h2>
        <div>
          <JSONPretty id="json-pretty" data={petition}></JSONPretty>
        </div>

        <h2>Latest Records ({latestRecords.length}):</h2>
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
