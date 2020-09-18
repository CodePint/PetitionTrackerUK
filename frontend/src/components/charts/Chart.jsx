import React, { useState, useEffect, useRef } from "react";
import ReactDOM from "react-dom";

import Chartjs from "chart.js";
import { chartConfig, dataConfig, chartColors } from "./config/LineChartConfig";
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

function Chart({ datasets, handleDatasetDeletion, toggleTotalSignatures, showTotalSigs }) {
  const chartContainer = useRef(null);
  const baseDataConfig = dataConfig;
  const [baseChartConfig, setBaseChartConfig] = useState(chartConfig);
  const [chartInstance, setChartInstance] = useState(null);
  const [legendValuesToggle, setLegendValuesToggle] = useState([]);

  const useFluidFont = true;
  const chartFontSizeRef = useRef(null);
  const windowWidthRef = useRef(null);
  const refDivElem = useRef(null);
  const refChartElem = useRef(null);

  useEffect(() => {
    if (useFluidFont) {
      window.addEventListener("resize", resizeFontForWindow);
      return () => {
        window.removeEventListener("resize", resizeFontForWindow);
      };
    }
  });

  useEffect(() => {
    if (useFluidFont) {
      windowWidthRef.current = window.innerWidth;
      setFontSize();
    }
  }, []);

  useEffect(() => {
    if (chartContainer && chartContainer.current) {
      const newChartInstance = new Chartjs(chartContainer.current, baseChartConfig);
      setChartInstance(newChartInstance);
    }
  }, [chartContainer, baseChartConfig]);

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

  function renderLegendCode(code, isToggled) {
    return !isToggled && code.length > 5 ? `${code.slice(0, 1)}${code.slice(-4)}` : code;
  }

  function lazyIntToCommaString(x) {
    return x ? x.toString().replace(/\B(?=(\d{3})+(?!\d))/g, ",") : "0";
  }

  function resizeFontForWindow() {
    let fontSize = window.getComputedStyle(refDivElem.current).fontSize;
    if (shouldResize([100, 100])) {
      setFontSize();
    }
  }

  function setFontSize() {
    let fontSize = window.getComputedStyle(refDivElem.current).fontSize;
    fontSize = fontSize.replace("px", "");
    fontSize = Math.round(fontSize / 1.5);

    let config = _.cloneDeep(baseChartConfig);
    config.options.scales.xAxes[0].ticks.fontSize = fontSize;
    config.options.scales.yAxes[0].ticks.fontSize = fontSize;
    chartFontSizeRef.current = fontSize;
    setBaseChartConfig(config);
  }

  function shouldResize(range) {
    const windowWidth = window.innerWidth;
    const lowerLimit = windowWidthRef.current - range[0] > windowWidth;
    const upperLimit = windowWidthRef.current + range[1] < windowWidth;

    if (lowerLimit || upperLimit) {
      windowWidthRef.current = windowWidth;
      return true;
    } else {
      return false;
    }
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

  function renderLegendItem(colorKey, value, meta, geography) {
    const isToggled = legendValuesToggle.includes(value);
    return (
      <li
        key={`${geography || ""}-legend- ${value}`}
        className={`${geography || ""} ${value} ${isToggled ? "expand" : ""}`}
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
              <FontAwesomeIcon className="fa-fw" icon={faPencilAlt} />
            </span>
            <span>{lazyIntToCommaString(meta.total || meta.count)}</span>
          </div>
        </div>

        <div className="expanded">
          {datasets.length > 1 ? renderLegendDeleteBtn(geography, value) : <div></div>}
        </div>
      </li>
    );
  }

  function renderLegendDeleteBtn(geography, value) {
    return (
      <div
        className="delete"
        onClick={() =>
          value === "Total" && !showTotalSigs
            ? toggleTotalSignatures()
            : handleDatasetDeletion(geography, value)
        }
      >
        <div>
          <FontAwesomeIcon className="fa-fw" icon={faTimesCircle} />
        </div>
      </div>
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
      <div className="legend">{renderLegend()}</div>
      <div
        ref={refChartElem}
        className="container"
        style={{ position: "relative", fontSize: chartFontSizeRef.current }}
      >
        <canvas ref={chartContainer} />
      </div>
      <div ref={refDivElem} style={{ fontSize: "1em" }}></div>
    </div>
  );
}

export default Chart;
