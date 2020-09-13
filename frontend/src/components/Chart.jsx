import React, { useState, useEffect, useRef } from "react";
import Chartjs from "chart.js";
// import "../styles/Chart.css";
import { chartConfig, dataConfig, chartColors } from "./LineChartConfig";
import _, { merge } from "lodash";
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import { faPencilAlt, faTimesCircle } from "@fortawesome/free-solid-svg-icons";

const totalSigDataConfig = {
  fill: false,
  borderColor: "rgb(40, 44, 52)",
  pointRadius: 1,
  pointHoverRadius: 20,
  borderWidth: 4,
};

function Chart({ datasets, banner, handleDatasetDeletion, toggleTotalSignatures }) {
  const chartContainer = useRef(null);
  const baseChartConfig = chartConfig;
  const baseDataConfig = dataConfig;
  const [chartInstance, setChartInstance] = useState(null);
  const [legendValuesToggle, setLegendValuesToggle] = useState([]);

  useEffect(() => {
    if (chartContainer && chartContainer.current) {
      const newChartInstance = new Chartjs(chartContainer.current, baseChartConfig);
      setChartInstance(newChartInstance);
    }
  }, [chartContainer]);

  useEffect(() => {
    if (chartInstance) {
      if (isValidInputs(datasets)) {
        datasets = datasets.map((data, index) => {
          let config = { ...baseDataConfig };
          data.borderColor = Object.values(chartColors)[index];
          if (data.label.includes("Total")) {
            config = merge(config, { ...totalSigDataConfig });
          }

          return merge(data, config);
        });
        chartInstance.data.datasets = datasets;
        chartInstance.update();
      } else {
        console.log(`Invalid input for chart: ${datasets}`);
      }
    }
  });

  function isValidInputs(input) {
    return input.length > 0 && !input.includes(null) && !input.includes(undefined);
  }

  function handleLegendToggle(value) {
    let toggled = [...legendValuesToggle];
    if (!legendValuesToggle.includes(value)) {
      toggled.push(value);
      setLegendValuesToggle(toggled);
    } else {
      toggled = toggled.filter((item) => item !== value);
      setLegendValuesToggle(toggled);
    }
  }

  function renderLegendCode(code, isToggled) {
    return !isToggled && code.length > 5 ? `${code.slice(0, 1)}${code.slice(-4)}` : code;
  }

  function renderLegendItem(colorKey, value, meta, geography) {
    const isToggled = legendValuesToggle.includes(value);
    // debugger;
    return (
      <li
        className={`dataset ${isToggled ? "expand" : ""}`}
        onClick={() => handleLegendToggle(value)}
      >
        <div className={`key ${value}`} style={{ background: colorKey }}>
          <div className="code">{renderLegendCode(meta.code, isToggled)}</div>
        </div>

        <div className="value">
          <span>{value}</span>
          <div className="count">
            <span className="dash">-</span>
            <span className="icon">
              <FontAwesomeIcon icon={faPencilAlt} />
            </span>
            <span>{meta.total || meta.count}</span>
          </div>
        </div>

        <div className="expanded">
          <div
            className="delete"
            onClick={() =>
              value === "Total" ? toggleTotalSignatures() : handleDatasetDeletion(geography, value)
            }
          >
            <div>
              <FontAwesomeIcon icon={faTimesCircle} />
            </div>
          </div>
        </div>
      </li>
    );
  }

  function renderLegend() {
    if (isValidInputs(datasets)) {
      return datasets.map((data) => {
        return renderLegendItem(data.borderColor, data.label, data.meta, data.geography);
      });
    }
  }

  return (
    <div className="Chart">
      <div className="banner">{banner()}</div>
      <div className="legend">{renderLegend()}</div>
      <div className="container" style={{ position: "relative" }}>
        <canvas ref={chartContainer} />
      </div>
    </div>
  );
}

export default Chart;
