import React, { useState, useEffect, useRef } from "react";
import Chartjs from "chart.js";
import "./css/Chart.css";
// import { barChartConfig } from "./BarChartConfig";
import lineChartConfig from "./LineChartConfig";

function Chart({ datasets }) {
  const chartContainer = useRef(null);
  const chartConfig = lineChartConfig;
  const [chartInstance, setChartInstance] = useState(null);

  useEffect(() => {
    if (chartContainer && chartContainer.current) {
      const newChartInstance = new Chartjs(chartContainer.current, chartConfig);
      setChartInstance(newChartInstance);
    }
  }, [chartContainer]);

  useEffect(() => {
    if (chartInstance) {
      if (datasets.length > 0) {
        chartInstance.data.datasets = datasets;
        chartInstance.update();
      }
    }
  });

  return (
    <div className="Chart">
      <canvas ref={chartContainer} />
    </div>
  );
}

export default Chart;
