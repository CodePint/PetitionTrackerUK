import React, { useState, useEffect, useRef } from "react";
import usePrev from "./utils/usePrev";
import useIsFirstRender from "./utils/useIsFirstRender";
import JSONPretty from "react-json-pretty";
import axios from "axios";
import "./css/Petition.css";
import Chart from "./charts/Chart";
import lineChartConfig from "./charts/LineChartConfig";
import _, { set, has, isNull } from "lodash";

function geoConfTemplate() {
  return {
    region: [],
    constituency: [],
    country: [],
  };
}

function Petition({ match }) {
  const petition_id = match.params.petition_id;
  const pollInterval = 60;

  const isFirstRender = useIsFirstRender();
  const isPollOverdue = useRef(true);
  const lastPolledAt = useRef(null);

  const showTotalSigs = useRef(true);
  const geoChartConfig = useRef(geoConfTemplate());
  const chartDataCache = useRef([]);
  const geoChartConfigCache = useRef(geoConfTemplate());

  const [petition, setPetition] = useState({});
  const [geoToAdd, setGeoToAdd] = useState(null);
  const [geoToDel, setGeoToDel] = useState(null);
  const [chartData, setChartData] = useState([]);
  const [chartTime, setChartTime] = useState({ days: 30 });

  const [chartError, setChartError] = useState({ status: false, error: { msg: "" } });
  function resetChartError() {
    setChartError({ status: false, error: { msg: "" } });
  }
  // Effect Hooks

  // Internal effects
  useEffect(() => {
    const interval = setInterval(() => {
      if (!isCacheValid()) {
        fetchandBuildFromConfig();
      }
    }, pollInterval);
    return () => clearInterval(interval);
  }, []);

  useEffect(() => {
    resetChartError();
  }, [chartData]);

  // User effects
  useEffect(() => {
    (async () => {
      const response = await fetchSignatures();
      if (response.status === 200) {
        let responseData = response.data;
        let datasets = [...chartData];
        let petitionData = responseData.petition;
        let totalSigData = buildTotalSignaturesDataset(responseData);
        datasets.push(totalSigData);
        updatePolledAt();
        updateChartCache(totalSigData);
        setPetition(petitionData);
        setChartData(datasets);
      } else if (response.status === 404) {
        let error = { msg: response.data };
        setChartError({ status: true, error: error });
      }
    })();
  }, []);

  useEffect(() => {
    if (geoToAdd) {
      (async () => {
        let data = null;
        const geography = geoToAdd.geography;
        const locale = geoToAdd.locale;

        const localeIsCached = existsInCachedGeoConf(geography, locale);
        const localeCacheData = fetchCachedDataset(locale);
        if (localeIsCached && localeCacheData) {
          data = localeCacheData;
        } else {
          data = await fetchAndBuildGeoData(geography, locale);
        }

        if (data) {
          let datasets = null;
          if (hasGeoConf()) {
            datasets = [...chartData];
          } else {
            showTotalSigs.current = false;
            datasets = [];
          }

          datasets.push(data);
          addToGeoConf(geography, locale);
          setChartData(datasets);
        }
      })();
    }
  }, [geoToAdd]);

  useEffect(() => {
    if (geoToDel) {
      let geography = geoToDel.geography;
      let locale = geoToDel.locale;
      if (isFinalInGeoConf()) {
        let data = fetchCachedDataset("Total");
        showTotalSigs.current = true;
        deleteFromGeoConf(geography, locale);
        setChartData([data]);
      } else {
        deleteFromGeoConf(geography, locale);
        let datasets = deleteDataSet(locale);
        setChartData(datasets);
      }
    }
  }, [geoToDel]);

  useEffect(() => {
    if (!isFirstRender) {
      fetchandBuildFromConfig();
    }
  }, [chartTime]);

  // Fetch/Build functions
  async function fetchAndBuildGeoData(geography, locale, allow404 = false) {
    let response = await fetchSignaturesBy(geography, locale);
    if (response.status === 200) {
      let data = buildGeographicDataset(response.data, geography);
      updateChartCache(data, geography, locale);
      return data;
    } else if (response.status === 404) {
      if (allow404) {
        return { label: toLabel(geography, locale, 0) };
      } else {
        setChartError({ status: true, error: { msg: response.log.msg } });
      }
    }
  }

  async function fetchandBuildFromConfig() {
    let datasets = [];
    let response = await fetchSignatures();
    if (response.status === 200) {
      let responseData = response.data;
      let geoData = await fetchSignaturesFromConfig();
      let sigData = buildTotalSignaturesDataset(responseData);

      datasets = datasets.concat(geoData);
      let datacache = [...datasets];
      (showTotalSigs.current ? datasets : datacache).push(sigData);
      chartDataCache.current = datacache;

      updatePolledAt();
      setPetition(responseData.petition);
      setChartData(datasets);
    } else if (response.status === 404) {
      let error = { msg: response.data.message };
      setChartError({ status: true, error: error });
    }
  }

  // API Fetch functions
  async function fetchSignatures() {
    let params = { since: chartTime };
    let url = `/petition/${petition_id}/signatures`;
    try {
      return await axios.get(url, { params: params });
    } catch (error) {
      if (error.response.status === 404) {
        console.log(error.response.data);
        return error.response;
      } else {
      }
    }
  }

  async function fetchSignaturesBy(geography, locale) {
    let params = { since: chartTime };
    let url = `/petition/${petition_id}/signatures_by/${geography}/${locale}`;
    try {
      return await axios.get(url, { params: params });
    } catch (error) {
      if (error.response.status === 404) {
        error.response.log = { msg: error.response.data.message, url: url, details: error };
        console.log(JSON.stringify(error.response.log));
        return error.response;
      } else if (error.response.status === 400) {
        let log = { msg: error.response.data.message, url: url, details: error };
        console.log(JSON.stringify(log));
        setChartError({ status: true, error: log });
      } else {
        let log = { msg: "Server Error", url: url, details: error };
        console.log(JSON.stringify(log));
        setChartError({ status: true, error: log });
      }
    }
  }

  async function fetchSignaturesFromConfig() {
    if (hasGeoConf) {
      let pending = [];
      Object.keys(geoChartConfig.current).forEach((geo) => {
        const locales = geoChartConfig.current[geo];
        let promises = locales.map(async (locale) => {
          return await fetchAndBuildGeoData(geo, locale, true);
        });
        pending.push(promises);
      });
      return await Promise.all(pending.flat());
    } else {
      return [];
    }
  }

  // Build dataset functions
  function buildTotalSignaturesDataset(input) {
    let data = {};
    const latestCount = input.meta.latest_data.total;
    data["label"] = `Total Signatures: ${latestCount}`;
    data["data"] = input.signatures.map((r) => ({
      x: r.timestamp,
      y: r.total,
    }));
    return data;
  }

  function buildGeographicDataset(input, geography) {
    let data = {};
    const choice = input.meta.query.locale;
    const latestCount = input.meta.latest_data.count;
    data["label"] = toLabel(choice.value, choice.code, latestCount);

    geography = "signatures_by_" + geography;
    data["data"] = input.signatures.map((r) => ({
      x: r.timestamp,
      y: r[geography].count,
    }));
    return data;
  }

  // Cache functions
  function updatePolledAt() {
    lastPolledAt.current = Math.round(new Date() / 1000);
    isPollOverdue.current = false;
  }

  function updateChartCache(dataset, geography = null, locale = null) {
    if (!fetchCachedDataset(geography, locale)) {
      let cache = [...chartDataCache.current];
      cache.push(dataset);
      chartDataCache.current = cache;
      if (geography && locale) {
        let geoCache = { ...geoChartConfigCache.current };
        geoCache[geography].push(locale);
        geoChartConfigCache.current = geoCache;
      }
    }
  }

  function isCacheValid() {
    const time_now = Math.round(new Date() / 1000);
    if (time_now - lastPolledAt.current > pollInterval) {
      isPollOverdue.current = true;
    } else {
      isPollOverdue.current = false;
    }
    return !isPollOverdue.current;
  }

  // Helper functions
  function toLabel(value, code, count = 0) {
    return `${value} (${code}) - ${count}`;
  }

  function flatGeoConf() {
    return Object.values(geoChartConfig.current).flat();
  }

  function hasGeoConf() {
    return flatGeoConf().length != 0;
  }

  function isFinalInGeoConf() {
    return flatGeoConf().length === 1;
  }

  function existsInGeoConf(geo, locale) {
    return geoChartConfig.current[geo].includes(locale);
  }

  function existsInCachedGeoConf(geo, locale) {
    return geoChartConfigCache.current[geo].includes(locale);
  }

  function deleteFromGeoConf(geography, locale) {
    let config = _.cloneDeep(geoChartConfig.current);
    config[geography] = config[geography].filter((item) => item !== locale);
    geoChartConfig.current = config;
  }

  function addToGeoConf(geography, locale) {
    let config = _.cloneDeep(geoChartConfig.current);
    config[geography].push(locale);
    geoChartConfig.current = config;
  }

  function findDataset(label) {
    return chartData.find((data) => data.label.includes(label));
  }

  function fetchCachedDataset(label) {
    return chartDataCache.current.find((data) => data.label.includes(label));
  }

  function deleteDataSet(locale) {
    let datasets = [...chartData];
    let index = datasets.findIndex((data) => data.label.includes(locale));
    if (index != -1) {
      datasets.splice(index, 1);
    }
    return datasets;
  }

  // Form Handlers
  const handleChartTimeForm = (event) => {
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

  const handleAddGeographiesForm = (event) => {
    event.preventDefault();
    const geography = event.target.geography.value;
    const locale = event.target.locale.value;
    if (existsInGeoConf(geography, locale)) {
      let error = { msg: `locale already configured: ${locale}` };
      setChartError({ status: true, error: error });
    } else {
      setGeoToAdd({ geography: geography, locale: locale });
    }
  };

  const handleDelGeographiesForm = (event) => {
    event.preventDefault();
    const { geography, locale } = JSON.parse(event.target.value);
    if (!existsInGeoConf(geography, locale)) {
      let error = { msg: `locale not configured: ${locale}` };
      setChartError({ status: true, error: error });
    } else {
      setGeoToDel({ geography: geography, locale: locale });
    }
  };

  function toggleTotalSignatures() {
    let found = findDataset("Total");
    if (!showTotalSigs.current && !found) {
      let data = null;
      let datasets = [...chartData];
      data = fetchCachedDataset("Total");
      datasets.push(data);
      showTotalSigs.current = true;
      setChartData(datasets);
    } else if (showTotalSigs.current && hasGeoConf() && found) {
      showTotalSigs.current = false;
      let datasets = deleteDataSet("Total");
      setChartData(datasets);
    }
  }

  // Presentation Helpers
  function dataSinceString() {
    if (chartTime["all"]) {
      return "All Time";
    } else {
      return Object.values(chartTime)[0] + " " + Object.keys(chartTime)[0];
    }
  }

  function renderChartError() {
    return <h3>{chartError.status.msg}</h3>;
  }

  return (
    <div className="Petition">
      <h1>Petition ID: {petition_id}</h1>
      <h1>Action: {petition["action"]}</h1>
      <h2>Total signatures: {petition["signatures"]}</h2>
      <div>{chartError.status ? renderChartError() : ""}</div>
      <div className="PetitionChart">
        <div className="ChangeChartTime">
          <form onSubmit={handleChartTimeForm}>
            <h3>View data since: {dataSinceString()}</h3>
            <select name="units">
              <option value="minutes">minutes</option>
              <option value="hours">hours</option>
              <option value="days">days</option>
              <option value="weeks">weeks</option>
            </select>

            <input type="text" name="amount" />
            <input type="submit" value="Submit" />
          </form>
          <button name="viewAll" value="all" onClick={handleChartTimeForm}>
            View All
          </button>
        </div>

        <br></br>
        <div>{chartError.error ? chartError.error.msg : ""}</div>

        <div className="ChartWrapper">
          <Chart datasets={chartData} />
        </div>

        <br></br>
      </div>

      <div className="addGeographiesForm">
        <form onSubmit={handleAddGeographiesForm}>
          <label htmlFor="geographyInput">Geography: &nbsp;</label>
          <input type="text" name="geography" id="geographyInput" />
          <br></br>
          <label htmlFor="localeInput">Locale: &nbsp;</label>
          <input type="text" name="locale" id="localeInput" />
          <br></br>

          <label htmlFor="showTotal">Show Total: &nbsp;</label>
          <input
            name="showTotal"
            type="checkbox"
            checked={showTotalSigs.current}
            onChange={toggleTotalSignatures}
          />
          <br></br>

          <input type="submit" value="Submit" />
        </form>
      </div>
      <br></br>
      <br></br>
      <div>
        <form className="delGeographiesForm">
          {Object.keys(geoChartConfig.current).map((geo) => {
            return (
              <div key={`${geo}-form`}>
                <h2>{geo}</h2>
                {geoChartConfig.current[geo].map((locale) => {
                  return (
                    <div key={`${geo}-${locale}-cb`}>
                      <label htmlFor={`${geo}-${locale}-cb`}>{locale} &nbsp;</label>
                      <input
                        id={`${geo}-${locale}-cb`}
                        value={JSON.stringify({
                          geography: geo,
                          locale: locale,
                        })}
                        name={locale}
                        type="checkbox"
                        checked={true}
                        onChange={handleDelGeographiesForm}
                      />
                    </div>
                  );
                })}
              </div>
            );
          })}
        </form>
      </div>
      <br></br>
      <div className="data">
        <h2>Petition data:</h2>
        <div>
          <JSONPretty id="json-pretty" data={petition}></JSONPretty>
        </div>
      </div>
    </div>
  );
}

export default Petition;
