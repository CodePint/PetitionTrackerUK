import React, { useState, useEffect, useRef } from "react";
import _, { set, has, isNull, last } from "lodash";
import axios from "axios";
import JSONPretty from "react-json-pretty";
import moment from "moment";
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import {
  faPencilAlt,
  faCalendarAlt,
  faCalendarTimes,
  faExternalLinkAlt,
  faAngleRight,
  faAngleDown,
  faLock,
  faUnlock,
  faTasks,
  faTrafficLight,
} from "@fortawesome/free-solid-svg-icons";

import useIsFirstRender from "./utils/useIsFirstRender";
import usePrev from "./utils/usePrev";
import ConstituenciesSrc from "../geographies/json/constituencies.json";
import RegionsSrc from "../geographies/json/regions.json";
import CountriesSrc from "../geographies/json/countries.json";

import Chart from "./Chart.jsx";
import GeoNav from "./GeoNav.jsx";
import ProgressBar from "./ProgressBar";

function geoConfTemplate() {
  return {
    region: [],
    constituency: [],
    country: [],
  };
}

function Petition({ match }) {
  const petition_id = match.params.petition_id;
  const CONSTITUENCIES = ConstituenciesSrc;
  const REGIONS = RegionsSrc;
  const COUNTRIES = CountriesSrc;
  const maxDatsets = 11;

  const isFirstRender = useIsFirstRender();
  const isPollOverdue = useRef(true);
  const lastPolledAt = useRef(null);
  const showTotalSigs = useRef(true);
  const geoChartConfig = useRef(geoConfTemplate());
  const chartDataCache = useRef([]);
  const geoChartConfigCache = useRef(geoConfTemplate());

  const [petition, setPetition] = useState({});
  const [sigToAdd, setGeoToAdd] = useState(null);
  const [sigToDel, setGeoToDel] = useState(null);
  const [chartData, setChartData] = useState([]);
  const [chartTime, setChartTime] = useState({ days: 30 });
  const [chartError, setChartError] = useState({ status: false, error: { msg: "" } });

  const [allTimeValueSelected, setAllTimeValueSelected] = useState(false);
  const [showAdditionalDetails, setShowAdditionalDetails] = useState(false);

  useEffect(() => {
    resetChartError();
  }, [chartData]);

  // User Effect Hooks
  useEffect(() => {
    fetchAndBuildBaseData();
  }, []);

  useEffect(() => {
    if (sigToAdd) {
      addChartDataset(sigToAdd);
    }
  }, [sigToAdd]);

  useEffect(() => {
    if (sigToDel) {
      delChartDataset(sigToDel);
    }
  }, [sigToDel]);

  useEffect(() => {
    if (!isFirstRender) {
      fetchAndBuildFromConfig();
    }
  }, [chartTime]);

  // Lifecycle functions
  function resetChartError() {
    setChartError({ status: false, error: { msg: "" } });
  }

  function resetCacheAndConfig() {
    showTotalSigs.current = true;
    chartDataCache.current = [];
    geoChartConfig.current = geoConfTemplate();
    geoChartConfigCache.current = geoConfTemplate();
  }

  // Cache functions
  function updatePolledAt() {
    lastPolledAt.current = new Date();
  }

  function updateChartCache(dataset) {
    const locale = dataset.meta.code;
    const geography = dataset.geography;
    if (!fetchCachedDataset(locale || "Total")) {
      let dataCache = [...chartDataCache.current];
      dataCache.push(dataset);
      chartDataCache.current = dataCache;
      if (geography && locale) {
        let geoCache = _.cloneDeep(geoChartConfigCache.current);
        geoCache[geography].push(dataset.meta);
        geoChartConfigCache.current = geoCache;
      }
    }
  }

  async function addChartDataset(geoLocale) {
    let data = null;
    const geography = geoLocale.geography;
    const locale = geoLocale.locale;

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
      addToGeoConf(geography, data.meta);
      setChartData(datasets);
    }
  }

  async function delChartDataset(geoLocale) {
    let geography = geoLocale.geography;
    let locale = geoLocale.locale;
    if (isFinalInGeoConf()) {
      let data = fetchCachedDataset("Total");
      showTotalSigs.current = true;
      delFromGeoConf(geography, locale);
      setChartData([data]);
    } else {
      delFromGeoConf(geography, locale);
      let datasets = deleteDataSet(locale);
      setChartData(datasets);
    }
  }

  async function fetchAndBuildBaseData() {
    updatePolledAt();
    const response = await fetchSignatures();
    if (response.status === 200) {
      updatePolledAt();
      resetCacheAndConfig();

      let datasets = [];
      let responseData = response.data;
      let petitionData = responseData.petition;
      let totalSigData = buildTotalSignaturesDataset(responseData);
      datasets.push(totalSigData);

      updateChartCache(totalSigData);
      setPetition(petitionData);
      setChartData(datasets);
    } else if (response.status === 404) {
      let error = JSON.stringify({ msg: response.data });
      setChartError({ status: true, error: error });
    }
  }

  // Fetch/Build functions
  async function fetchAndBuildGeoData(geography, locale, allow404 = false) {
    let response = await fetchSignaturesBy(geography, locale);
    if (response.status === 200) {
      let data = buildGeographicDataset(response.data, geography);
      updateChartCache(data);
      return data;
    } else if (response.status === 404) {
      if (allow404) {
        // Handles a locale that does not have data for query
        // Needs further testing and a locale lookup
        return {
          data: [],
          geography: geography,
          key: locale,
          locale: locale,
          meta: { code: "", count: 0, name: locale, timestamp: "" },
        };
      } else {
        setChartError({ status: true, error: { msg: JSON.stringify(response.log.msg) } });
      }
    }
  }

  async function fetchAndBuildFromConfig() {
    updatePolledAt();
    let response = await fetchSignatures();
    if (response.status === 200) {
      let datasets = [];
      let responseData = response.data;
      let geoConfig = geoConfTemplate();
      let geoData = await fetchSignaturesFromConfig();
      geoChartConfig.current = geoConfig;
      geoChartConfigCache.current = geoConfig;
      let totalSigData = buildTotalSignaturesDataset(responseData);

      let sigData = buildTotalSignaturesDataset(responseData);
      datasets = datasets.concat(geoData);
      geoData.forEach((data) => {
        geoConfig[data.geography].push(data.meta);
      });

      let datacache = _.cloneDeep(datasets);
      datacache.push(totalSigData);
      if (showTotalSigs.current) {
        datasets.push(totalSigData);
      }

      // To Do:
      // Reindex new datasets against old chartData
      chartDataCache.current = datacache;
      setPetition(responseData.petition);
      setChartData(datasets);
    } else if (response.status === 404) {
      let error = { msg: JSON.stringify(response.data.message) };
      setChartError({ status: true, error: error });
    }
  }

  // API Fetch functions
  async function fetchSignatures() {
    let params = {};
    let url = `/petition/${petition_id}/signatures`;
    if (chartTime) {
      let now = moment(lastPolledAt.current).format("DD-MM-YYYYThh:mm:ss");
      params["since"] = { since: chartTime, now: now };
    }
    try {
      return await axios.get(url, { params: params });
    } catch (error) {
      if (error.response.status === 404) {
        console.log(error.response.data);
        return error.response;
      } else {
        let log = { msg: "Server Error", url: url, details: error };
        console.log(JSON.stringify(log));
        setChartError({ status: true, error: log });
        return error.response;
      }
    }
  }

  async function fetchSignaturesBy(geography, locale) {
    let params = {};
    let url = `/petition/${petition_id}/signatures_by/${geography}/${locale}`;
    if (chartTime) {
      let now = moment(lastPolledAt.current).format("DD-MM-YYYYThh:mm:ss");
      params["since"] = { since: chartTime, now: now };
    }
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
        return error.response;
      } else {
        let log = { msg: "Server Error", url: url, details: error };
        console.log(JSON.stringify(log));
        setChartError({ status: true, error: log });
        return error.response;
      }
    }
  }

  async function fetchSignaturesFromConfig() {
    if (hasGeoConf()) {
      console.log("fetching from config");
      let pending = [];
      Object.keys(geoChartConfig.current).forEach((geo) => {
        const locales = geoChartConfig.current[geo];
        let promises = locales.map(async (locale) => {
          return await fetchAndBuildGeoData(geo, locale.code, true);
        });
        pending.push(promises);
      });
      console.log("fetch from config completed");
      return await Promise.all(pending.flat());
    } else {
      return [];
    }
  }

  // Build dataset functions
  function buildTotalSignaturesDataset(input) {
    let dataset = {};
    let dataset_name = "Total";
    dataset.key = dataset_name;
    dataset.label = dataset_name;
    dataset.meta = input.meta.latest_data;
    dataset.meta.name = dataset_name;
    dataset.meta.code = "T";

    if (dataset.meta.total === 0) {
      dataset.data = [];
    } else {
      dataset.data = input.signatures.map((r) => ({
        x: r.timestamp,
        y: r.total,
      }));
    }
    return dataset;
  }

  function buildGeographicDataset(input, geography) {
    let dataset = {};
    const choice = input.meta.query.locale;
    dataset.meta = input.meta.latest_data;
    dataset.geography = geography;
    dataset.key = `${choice.value}-${choice.code}`;
    dataset.label = choice.value;
    if (dataset.meta.count === 0) {
      dataset.data = [];
    } else {
      geography = "signatures_by_" + geography;
      dataset.data = input.signatures.map((r) => ({
        x: r.timestamp,
        y: r[geography].count,
      }));
    }
    return dataset;
  }

  // Helper functions

  function lazyIntToCommaString(x) {
    return x ? x.toString().replace(/\B(?=(\d{3})+(?!\d))/g, ",") : "";
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
    return geoChartConfig.current[geo].find(
      (data) => data && (data.name === locale || data.code === locale)
    );
  }

  function existsInCachedGeoConf(geo, locale) {
    return geoChartConfigCache.current[geo].find(
      (data) => data && (data.name === locale || data.code === locale)
    );
  }

  function delFromGeoConf(geography, locale) {
    let config = _.cloneDeep(geoChartConfig.current);
    let configArray = [...config[geography]];
    configArray = config[geography].filter((data) => {
      return data && data.name !== locale && data.code !== locale;
    });
    config[geography] = configArray;
    geoChartConfig.current = config;
  }

  function addToGeoConf(geography, data) {
    let config = _.cloneDeep(geoChartConfig.current);
    config[geography].push(data);
    geoChartConfig.current = config;
  }

  function findDataset(identifier) {
    return chartData.find((data) => data && data.label.includes(identifier));
  }

  function fetchCachedDataset(identifier) {
    return chartDataCache.current.find((data) => data && data.label.includes(identifier));
  }

  function deleteDataSet(locale) {
    let datasets = [...chartData];
    let index = datasets.findIndex((data) => data && data.label.includes(locale));
    if (index != -1) {
      datasets.splice(index, 1);
    }
    return datasets;
  }

  function getThresholdStatus() {
    const thresholds = thresholdStatus();
    if (!thresholds) {
      return "N/A";
    } else if (thresholds.debate.outcome) {
      return "Debate Completed";
    } else if (thresholds.debate.scheduled) {
      return "Awaiting Debate";
    } else if (thresholds.debate.reached) {
      return "Debate Threshold Reached";
    } else if (thresholds.response.responded) {
      return "Government Responded";
    } else if (thresholds.response.reached) {
      return "Awaiting Response";
    } else {
      return "Attracting signatures";
    }
  }

  // Form Handlers
  const toggleTotalSignatures = (event) => {
    let found = findDataset("Total");

    if (!showTotalSigs.current && !found) {
      let data = null;
      let datasets = [...chartData];
      data = fetchCachedDataset("Total");

      if (data) {
        datasets.push(data);
        showTotalSigs.current = true;
        setChartData(datasets);
      } else {
        let error = { msg: "Could not find cache for Total Signature, Please refresh." };
        setChartError({ status: true, error: error });
      }
    } else if (showTotalSigs.current && hasGeoConf() && found) {
      showTotalSigs.current = false;
      let datasets = deleteDataSet("Total");
      setChartData(datasets);
    }
  };

  const handleChartTimeForm = (event) => {
    event.preventDefault();
    if (event.target.units.value === "all") {
      setChartTime(null);
    } else {
      let chartTimeObj = {};
      let timeAmount = event.target.amount.value;
      let timeUnit = event.target.units.value;
      const intRegex = new RegExp("^[0-9]+$");
      if (intRegex.test(timeAmount)) {
        chartTimeObj[timeUnit] = parseInt(timeAmount);
        setChartTime(chartTimeObj);
      } else {
        let error = { msg: "Invalid input (time must be a number)" };
        setChartError({ status: true, error: error });
      }
    }
  };

  const handleAddGeoSigForm = (geography, locale) => {
    // event.preventDefault();
    // const geography = event.target.geography.value;
    // const locale = event.target.locale.value;
    const found = existsInGeoConf(geography, locale);
    if (flatGeoConf().length >= maxDatsets) {
      let error = { msg: `Max datsets (${maxDatsets}) reached` };
      setChartError({ status: true, error: error });
    } else if (found) {
      let error = { msg: `locale already configured: ${found.name} (${found.code})` };
      setChartError({ status: true, error: error });
    } else {
      setGeoToAdd({ geography: geography, locale: locale });
    }
  };

  const handleDelGeoSigForm = (event) => {
    event.preventDefault();
    const { geography, locale } = JSON.parse(event.target.value);
    if (!existsInGeoConf(geography, locale)) {
      let error = { msg: `locale not configured: ${locale}` };
      setChartError({ status: true, error: error });
    } else {
      setGeoToDel({ geography: geography, locale: locale });
    }
  };

  const handleRefreshChartForm = (event) => {
    event.preventDefault();
    fetchAndBuildFromConfig();
  };

  const handleResetChartForm = (event) => {
    event.preventDefault();
    fetchAndBuildBaseData();
  };

  // Render Functions
  function dataSinceString() {
    if (chartTime) {
      return Object.values(chartTime)[0] + " " + Object.keys(chartTime)[0];
    } else {
      return "All Time";
    }
  }

  function petitionJSON() {
    return (
      <div className="data">
        <h2>Petition data:</h2>
        <div>
          <JSONPretty id="json-pretty" data={petition}></JSONPretty>
        </div>
      </div>
    );
  }

  function renderToggleTotalSigForm() {
    return (
      <form>
        <label htmlFor="showTotal">Show Total: &nbsp;</label>
        <input
          name="showTotal"
          type="checkbox"
          checked={showTotalSigs.current}
          onChange={toggleTotalSignatures}
        />
        <br></br>
      </form>
    );
  }

  const isChartTimeViewAll = (event) => {
    event.preventDefault();
    if (event.target.value === "all") {
      setAllTimeValueSelected(true);
    } else if (allTimeValueSelected) {
      setAllTimeValueSelected(false);
    }
  };

  function renderChartTimeForm() {
    return (
      <div className="chartTimeForm">
        <form onSubmit={handleChartTimeForm}>
          <h3>View data since: {dataSinceString()}</h3>
          <select name="units" onChange={isChartTimeViewAll}>
            <option value="minutes">minutes</option>
            <option value="hours">hours</option>
            <option value="days">days</option>
            <option value="weeks">weeks</option>
            <option value="all">all time</option>
          </select>

          <input type="text" name="amount" disabled={allTimeValueSelected} />
          <input type="submit" value="Submit" />
        </form>
      </div>
    );
  }

  function renderResetChartForm() {
    return (
      <div className="resetChartForm">
        <form>
          <button name="reset" value="reset" onClick={handleResetChartForm}>
            Reset Chart
          </button>
        </form>
      </div>
    );
  }

  function renderRefreshChartForm() {
    return (
      <div className="refreshChartForm">
        <form>
          <button name="refresh" value="refresh" onClick={handleRefreshChartForm}>
            Refresh Chart
          </button>
        </form>
      </div>
    );
  }

  function formatDate(date) {
    return moment(date).format("DD-MM-YYYY");
  }

  function addTimeToDate(date, value, unit) {
    return moment(date).add(value, unit);
  }

  function thresholdStatus() {
    if (!_.isEmpty(petition)) {
      return {
        response: {
          reached: petition.response_threshold_reached_at,
          responded: petition.government_response_at,
        },
        debate: {
          reached: petition.debate_threshold_reached_at,
          scheduled: petition.scheduled_debate_date,
          outcome: petition.debate_outcome_at,
        },
      };
    } else {
      return null;
    }
  }

  function renderPetitionAction() {
    return (
      <div className="action">
        <h1>
          <span>{petition.action} </span>
          <span> &nbsp;</span>
          <span className="icon">
            <a href={petition.url}>
              <FontAwesomeIcon icon={faExternalLinkAlt} />
            </a>
          </span>
        </h1>
      </div>
    );
  }

  function renderMetaSection() {
    return (
      <div className="meta">
        <div className="created_at flex-child">
          <div>
            <h5>
              <span className="icon">
                <FontAwesomeIcon icon={faCalendarAlt} />
              </span>
              <span className="title">Created</span>
            </h5>
            <div className="values">{moment(petition.pt_created_at).format("DD MMMM, YYYY")}</div>
          </div>
        </div>
        <div className="state flex-child">
          <div>
            <h5>
              {" "}
              <span className="icon">
                {" "}
                <FontAwesomeIcon icon={faTrafficLight} />
              </span>
              <span className="title">State</span>
            </h5>
            <div className="values">
              <span>{_.capitalize(petition.state)}</span>
              <span className="icon">
                {" "}
                <FontAwesomeIcon icon={petition.state === "open" ? faUnlock : faLock} />
              </span>
            </div>
          </div>
        </div>
        <div className="deadline_at flex-child">
          <div>
            <h5>
              <span className="icon">
                {" "}
                <FontAwesomeIcon icon={faCalendarTimes} />
              </span>
              <span className="title">Deadline</span>
            </h5>
            <div className="values">
              {addTimeToDate(petition.pt_created_at, 6, "months").format("DD MMMM, YYYY")}
            </div>
          </div>
        </div>
        <div className="progress flex-child">
          <div>
            <h5>
              <span className="icon">
                {" "}
                <FontAwesomeIcon icon={faTasks} />
              </span>
              <span className="title">Progress</span>
            </h5>
            <div className="values">{getThresholdStatus()}</div>
          </div>
        </div>
      </div>
    );
  }

  function renderProgressBars() {
    return (
      <div className="progress">
        <div className="thresholds">
          <ProgressBar
            play={true}
            label={{ text: "Government will respond at 10,000 signatures", icon: "crown" }}
            start={0}
            threshold={10000}
            progress={petition.signatures}
          ></ProgressBar>
          <ProgressBar
            play={true}
            label={{
              text: "Parliament will consider debate at 100,000 signatures",
              icon: "portcullis",
            }}
            start={0}
            threshold={100000}
            progress={petition.signatures}
          ></ProgressBar>
        </div>
      </div>
    );
  }

  function renderPetitionText() {
    return (
      <div className="text">
        <div className="background">
          {petition.background}
          <div
            className="details-toggle"
            onClick={() => setShowAdditionalDetails(!showAdditionalDetails)}
          >
            {" "}
            <span className="icon">
              <FontAwesomeIcon icon={showAdditionalDetails ? faAngleDown : faAngleRight} />
            </span>
            <span>{showAdditionalDetails ? "Less" : "More"} details</span>
          </div>
        </div>
        <div
          className="additional-details"
          style={showAdditionalDetails ? {} : { display: "none" }}
        >
          {petition.additional_details}
        </div>
      </div>
    );
  }

  function renderChartBanner() {
    return (
      <div className="wrapper">
        <div className="id">
          <h3># {petition_id}</h3>
        </div>
        <div className="signatures">
          <span className="icon">
            <FontAwesomeIcon icon={faPencilAlt} />
          </span>
          <h3>{lazyIntToCommaString(petition.signatures)}</h3>
        </div>
      </div>
    );
  }

  return (
    <div className="Petition">
      {renderPetitionAction()}

      <div className="signatures-heading">
        <span className="icon">
          <FontAwesomeIcon icon={faPencilAlt} />
        </span>
        <h3>{lazyIntToCommaString(petition.signatures)} signatures</h3>
      </div>
      {renderProgressBars()}
      {renderPetitionText()}
      {renderMetaSection()}
      <br></br>

      <div className="petition__chart">
        <Chart datasets={chartData} banner={renderChartBanner} />
      </div>

      <div className="petition__geonav">
        <GeoNav
          geoSearchHandler={handleAddGeoSigForm}
          geoDeleteHandler={handleDelGeoSigForm}
          geoConfig={geoChartConfig.current}
        ></GeoNav>
      </div>

      <div className="ChartNav">
        <br></br>
        <br></br>
        <div>{renderChartTimeForm()}</div>
        <div>{renderRefreshChartForm()}</div>
        <div>{renderResetChartForm()}</div>
        <div>{renderToggleTotalSigForm()}</div>
      </div>

      <div className="chart__error">
        <div>
          <h4>{chartError.error ? chartError.error.msg : ""}</h4>
        </div>
      </div>
    </div>
  );
}

export default Petition;
