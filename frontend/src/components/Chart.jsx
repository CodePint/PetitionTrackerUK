import React, { useState, useEffect, useRef } from "react";
import Chartjs from "chart.js";
// import "../styles/Chart.css";
import { chartConfig, dataConfig, chartColors } from "./LineChartConfig";
import _, { merge } from "lodash";

const totalSigDataConfig = {
  fill: false,
  borderColor: "rgb(40, 44, 52)",
  pointRadius: 1,
  pointHoverRadius: 20,
  borderWidth: 4,
};

function Chart({ datasets, banner = null }) {
  const chartContainer = useRef(null);
  const baseChartConfig = chartConfig;
  const baseDataConfig = dataConfig;
  const [chartInstance, setChartInstance] = useState(null);
  const [legendValueToggle, setLegendValueToggle] = useState(null);

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

  function renderLegendItem(colorKey, value, meta) {
    return (
      <li
        className={`dataset ${legendValueToggle === value ? "expand" : ""}`}
        onClick={() => {
          setLegendValueToggle(value);
        }}
      >
        <div className={`key key-${value}`} style={{ background: colorKey }}>
          <div>{meta.code.slice(0, 3)}</div>
        </div>
        <div className="value">{value}</div>
      </li>
    );
  }

  function renderLegend() {
    if (isValidInputs(datasets)) {
      return datasets.map((data) => {
        return renderLegendItem(data.borderColor, data.label, data.meta);
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
