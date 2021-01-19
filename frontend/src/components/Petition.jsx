import React, { useState, useEffect, useRef } from "react";
import ReactDOM from "react-dom";
import { Redirect, useHistory } from "react-router-dom";
import axios from "axios";
import _ from "lodash";
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
  faSyncAlt,
  faExclamationTriangle,
} from "@fortawesome/free-solid-svg-icons";

import useIsFirstRender from "./utils/useIsFirstRender";
import ConstituenciesJSON from "./data/geographies/constituencies.json";
import RegionsJSON from "./data/geographies/regions.json";
import CountriesJSON from "./data/geographies/countries.json";

import Chart from "./charts/Chart.jsx";
import GeoNav from "./GeoNav.jsx";
import ProgressBar from "./ProgressBar";
import TimeNav from "./TimeNav";

function geographiesJSON() {
  return {
    country: CountriesJSON,
    constituency: ConstituenciesJSON,
    region: RegionsJSON,
  };
}

function Petition({ match }) {
  const petition_id = match.params.petition_id;
  const API_URL_PREFIX = process.env.REACT_APP_FLASK_API_URL_PREFIX || "";

  const maxDatsets = 11;
  const isFirstRender = useIsFirstRender();
  const History = useHistory();

  const lastPolledAt = useRef(new Date());
  const showTotalSigs = useRef(true);
  const chartDataCache = useRef([]);
  const geoChartConfig = useRef(geoConfTemplate());
  const geoChartConfigCache = useRef(geoConfTemplate());
  const geoNavSortConfig = useRef(baseGeoNavConfig());

  const [geoNavInput, setGeoNavInput] = useState({ constituency: [], country: [], region: [] });
  const [petition, setPetition] = useState({});
  const [localeToAdd, setLocaleToAdd] = useState(null);
  const [localeToDel, setLocaleToDel] = useState(null);

  const [chartData, setChartData] = useState([]);
  const [chartTime, setChartTime] = useState(defaultChartTime());
  const [petitionNotFound, setPetitionNotFound] = useState(false);
  const [showAdditionalDetails, setShowAdditionalDetails] = useState(false);
  const [chartError, setChartError] = useState({
    status: false,
    error: { msg: "" },
  });

  function geoConfTemplate() {
    return {
      region: [],
      constituency: [],
      country: [],
    };
  }

  const presetTimeOpts = [
    { unit: "hours", value: 24, selected: false },
    { unit: "days", value: 7, selected: false },
    { unit: "days", value: 30, selected: true },
    { unit: "days", value: 90, selected: false },
    { unit: "All time", value: null, selected: false },
  ];

  useEffect(() => {
    resetChartError();
  }, [chartData]);

  // User Effect Hooks
  useEffect(() => {
    fetchAndBuildBaseData();
  }, []);

  useEffect(() => {
    if (localeToAdd) {
      addChartDataset(localeToAdd);
    }
  }, [localeToAdd]);

  useEffect(() => {
    if (localeToDel) {
      delChartDataset(localeToDel);
    }
  }, [localeToDel]);

  useEffect(() => {
    if (!isFirstRender) {
      ReactDOM.unstable_batchedUpdates(() => {
        fetchAndBuildFromConfig().then((results) => {
          if (results) {
            setGeoNavInput(results.geoNav);
            setPetition(results.petition);
            setChartData(results.datasets);
          }
        });
      });
    }
  }, [chartTime]);

  // Lifecycle functions
  function resetChartError() {
    setChartError({ status: false, error: { msg: "" } });
  }

  function redirectPetition404() {
    History.push("/");
    return <Redirect push to={`/petition/error/404/${petition_id}`}></Redirect>;
  }

  function defaultChartTime() {
    const defaults = { unit: "days", value: 30 };
    return {
      from: subtractTimeFromDate(defaults.value, defaults.unit).toDate(),
      to: null,
    };
  }

  function baseGeoNavConfig() {
    return {
      country: { col: "total", order: "DESC" },
      constituency: { col: "total", order: "DESC" },
      region: { col: "total", order: "DESC" },
    };
  }

  function resetCacheAndConfig() {
    showTotalSigs.current = true;
    chartDataCache.current = [];
    geoChartConfig.current = geoConfTemplate();
    geoChartConfigCache.current = geoConfTemplate();
  }

  // Cache functions
  function updatePolledAt(date = null) {
    lastPolledAt.current = date || new Date();
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
    const prevPoll = lastPolledAt.current;
    updatePolledAt();

    let geoNavData = null;
    const petitionResponse = await fetchPetition();

    if (petitionResponse.status === 200) {
      geoNavData = buildGeoNavData(petitionResponse.data.signatures);
    } else if (petitionResponse.status === 404) {
      lastPolledAt.current = prevPoll;
      setPetitionNotFound(true);
      return false;
    } else {
      lastPolledAt.current = prevPoll;
      let error = { msg: "Server Error" };
      setChartError({ status: true, error: error });
      return false;
    }

    const response = await fetchSignatures();
    if (response.status === 200) {
      resetCacheAndConfig();

      let datasets = [];
      let responseData = response.data;
      let petitionData = responseData.petition;
      let totalSigData = buildTotalSignaturesDataset(responseData);
      datasets.push(totalSigData);

      updateChartCache(totalSigData);
      setPetition(petitionData);
      setChartData(datasets);
      setGeoNavInput(geoNavData);
    } else {
      updatePolledAt(prevPoll);
      console.log(response.error);
      if (response.status === 404) {
        let error = { msg: "No signature data found" };
        setChartError({ status: true, error: error });
      } else {
        let error = { msg: "Server Error" };
        setChartError({ status: true, error: error });
      }
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
        return {
          data: [],
          geography: geography,
          key: locale,
          label: locale,
          meta: { code: "", count: 0, name: locale, timestamp: "" },
        };
      } else {
        console.log(response.error);
        let error = { msg: `No signatures found for: ${locale}` };
        setChartError({ status: true, error: error });
      }
    }
  }

  async function fetchAndBuildFromConfig() {
    const prevPoll = lastPolledAt.current;
    updatePolledAt();
    let geoNavData = null;
    const petitionResponse = await fetchPetition();
    if (petitionResponse.status === 200) {
      geoNavData = buildGeoNavData(petitionResponse.data.signatures);
    } else if (petitionResponse.status === 404) {
      setPetitionNotFound(true);
      return false;
    } else {
      let error = { msg: "Server Error" };
      setChartError({ status: true, error: error });
      return false;
    }

    let response = await fetchSignatures();
    if (response.status === 200) {
      let datasets = [];
      let responseData = response.data;
      let geoConfig = geoConfTemplate();

      let geoData = await fetchSignaturesFromConfig();
      geoChartConfig.current = geoConfig;
      geoChartConfigCache.current = geoConfig;
      let totalSigData = buildTotalSignaturesDataset(responseData);

      datasets = datasets.concat(geoData);
      geoData.forEach((data) => {
        geoConfig[data.geography].push(data.meta);
      });

      let datacache = _.cloneDeep(datasets);
      datacache.push(totalSigData);
      if (showTotalSigs.current) {
        datasets.push(totalSigData);
      }
      chartDataCache.current = datacache;

      return {
        geoNav: geoNavData,
        petition: petitionResponse.data.petition,
        datasets: datasets,
      };
    } else {
      updatePolledAt(prevPoll);
      console.log(response.error);
      if (response.status === 404) {
        let error = { msg: "No signature data found" };
        setChartError({ status: true, error: error });
      } else {
        let error = { msg: "Server Error" };
        setChartError({ status: true, error: error });
      }
    }
  }

  function buildGeoNavData(data) {
    let result = {};
    let defaultGeographies = geographiesJSON();
    Object.keys(defaultGeographies).forEach((geo) => {
      let defaultLocales = defaultGeographies[geo];
      let responseLocales = data[`signatures_by_${geo}`];

      let responseResult = responseLocales.map((locale) => {
        delete defaultLocales[locale.code];
        return { key: locale.code, value: locale.name, total: locale.count, type: geo };
      });

      let defaultResult = Object.entries(defaultLocales).map((locale) => {
        return { key: locale[0], value: locale[1], total: 0, type: geo };
      });
      let geoResult = defaultResult.concat(responseResult);

      const sortConfig = geoNavSortConfig.current[geo];
      geoResult = sortGeoInput(geoResult, sortConfig.col, sortConfig.order);
      result[geo] = geoResult;
    });
    return result;
  }

  // API Fetch functions
  async function fetchSignatures(params = {}) {
    let url = `${API_URL_PREFIX}/petition/${petition_id}/signatures`;
    params.timestamp = {
      gt: moment(chartTime.from).format("DD-MM-YYYYTH:m:ss"),
      lt: moment(getChartTimeTo()).format("DD-MM-YYYYTH:m:ss"),
    };
    console.log("fetching signatures!!");
    try {
      return await axios.get(url, { params: params });
    } catch (error) {
      if (error.response.status === 404) {
        console.log(error.response.data);
        return error.response;
      }
    }
  }

  async function fetchPetition(params = {}) {
    let url = `${API_URL_PREFIX}/petition/${petition_id}`;
    params.signatures = true;
    if (chartTime.to) {
      params.timestamp = moment(getChartTimeTo()).format("DD-MM-YYYYTH:m:ss");
      console.log(params.timestamp);
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

  async function fetchSignaturesBy(geography, locale, params = {}) {
    let url = `${API_URL_PREFIX}/petition/${petition_id}/signatures_by/${geography}/${locale}`;
    params.timestamp = {
      gt: moment(chartTime.from).format("DD-MM-YYYYTH:m:ss"),
      lt: moment(getChartTimeTo()).format("DD-MM-YYYYTH:m:ss"),
    };
    try {
      console.log("fetching signatures by", geography, "-", locale);
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
      console.log("0 items found");
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
    const choice = input.meta.locale;
    const latestData = input.meta.latest_data;
    const geo_key = "signatures_by_" + geography;

    dataset.meta = { ...latestData[geo_key], timestamp: latestData.timestamp };
    dataset.geography = geography;
    dataset.key = `${choice.value}-${choice.code}`;
    dataset.label = choice.value;
    if (dataset.meta.count === 0) {
      dataset.data = [];
    } else {
      dataset.data = input.signatures.map((r) => ({
        x: r.timestamp,
        y: r[geo_key].count,
      }));
    }
    return dataset;
  }

  // Helper functions
  function lazyIntToCommaString(x) {
    return x ? x.toString().replace(/\B(?=(\d{3})+(?!\d))/g, ",") : "0";
  }

  function flatGeoConf() {
    return Object.values(geoChartConfig.current).flat();
  }

  function hasGeoConf() {
    return flatGeoConf().length !== 0;
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

  function addTimeToDate(value, unit, date = new Date()) {
    return moment(date).add(value, unit);
  }

  function subtractTimeFromDate(value, unit, date = new Date()) {
    return moment(date).subtract(value, unit);
  }

  function getChartTimeTo() {
    if (petition.state === "closed") {
      return new Date(petition.pt_closed_at);
    } else if (chartTime.to) {
      return chartTime.to;
    } else {
      return lastPolledAt.current;
    }
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
    if (index !== -1) {
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

  function timeNavConfig() {
    if (!_.isEmpty(petition)) {
      return {
        minDate: moment(petition.pt_created_at, "YYYY-MM-DDThh:mm:ss").toDate(),
        maxDate:
          petition.state === "open"
            ? lastPolledAt.current
            : moment(petition.pt_closed_at, "YYYY-MM-DDThh:mm:ss").toDate(),
      };
    } else {
      return {};
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

  const handleChartTimeChange = (newTimeRange) => {
    setChartTime(newTimeRange);
  };

  const handleAddGeoSigForm = (geography, locale) => {
    const found = existsInGeoConf(geography, locale);
    if (flatGeoConf().length >= maxDatsets) {
      let error = { msg: `Max datsets (${maxDatsets}) reached` };
      setChartError({ status: true, error: error });
    } else if (found) {
      let error = { msg: `locale already configured: ${found.name} (${found.code})` };
      setChartError({ status: true, error: error });
    } else {
      setLocaleToAdd({ geography: geography, locale: locale });
    }
  };

  const handleDelGeoSigForm = (geography, locale) => {
    if (geography && locale) {
      if (!existsInGeoConf(geography, locale)) {
        let error = { msg: `locale not configured: ${locale}` };
        setChartError({ status: true, error: error });
      } else {
        setLocaleToDel({ geography: geography, locale: locale });
      }
    }
  };

  const handleSyncChartForm = () => {
    fetchAndBuildFromConfig();
  };

  function sortGeoInput(items, key, order) {
    let sorted = null;
    sorted = items.sort((a, b) => {
      if (a[key] < b[key]) {
        return order === "ASC" ? -1 : 1;
      }
      if (a[key] > b[key]) {
        return order === "ASC" ? 1 : -1;
      }
      return 0;
    });
    return sorted;
  }

  const handleGeoNavSortBy = (value) => {
    const params = JSON.parse(value);
    let input = _.cloneDeep(geoNavInput);
    let geoInput = input[params.geo];
    input[params.geo] = sortGeoInput(geoInput, params.col, params.order);
    geoNavSortConfig.current[params.geo] = { col: params.col, order: params.order };
    setGeoNavInput(input);
  };

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

  // Render Functions
  function renderPetitionAction() {
    return (
      <div className="action">
        <h1>
          <span>{petition.action} </span>
          <span> &nbsp;</span>
          <span className="icon">
            <a href={petition.url}>
              <FontAwesomeIcon className="fa-fw" icon={faExternalLinkAlt} />
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
                <FontAwesomeIcon className="fa-fw" icon={faCalendarAlt} />
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
                <FontAwesomeIcon className="fa-fw" icon={faTrafficLight} />
              </span>
              <span className="title">State</span>
            </h5>
            <div className="values">
              <span>{_.capitalize(petition.state)}</span>
              <span className="icon">
                {" "}
                <FontAwesomeIcon
                  className="fa-fw"
                  icon={petition.state === "open" ? faUnlock : faLock}
                />
              </span>
            </div>
          </div>
        </div>
        <div className="deadline_at flex-child">
          <div>
            <h5>
              <span className="icon">
                {" "}
                <FontAwesomeIcon className="fa-fw" icon={faCalendarTimes} />
              </span>
              <span className="title">Deadline</span>
            </h5>
            <div className="values">
              {addTimeToDate(6, "months", petition.pt_created_at).format("DD MMMM, YYYY")}
            </div>
          </div>
        </div>
        <div className="progress flex-child">
          <div>
            <h5>
              <span className="icon">
                {" "}
                <FontAwesomeIcon className="fa-fw" icon={faTasks} />
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
              <FontAwesomeIcon
                className="fa-fw"
                icon={showAdditionalDetails ? faAngleDown : faAngleRight}
              />
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

  function refreshChartBtn() {
    return (
      <button name="sync" value="sync" onClick={handleSyncChartForm}>
        <div className="icon sync" alt="sync">
          <span>
            <FontAwesomeIcon className="fa-fw" icon={faSyncAlt} />
          </span>
        </div>
      </button>
    );
  }

  function renderChartBannerNav() {
    return (
      <div className="wrapper">
        <div className="signatures">
          <input
            name="showTotal"
            id="showTotal"
            type="checkbox"
            checked={!showTotalSigs.current}
            readOnly={true}
            onClick={toggleTotalSignatures}
          />
          <label htmlFor="showTotal">
            <div className="icon-wrapper">
              <span className="icon">
                <FontAwesomeIcon className="fa-fw" icon={faPencilAlt} />
              </span>
            </div>
          </label>
        </div>

        <div className="id">
          <h3># {petition_id}</h3>
        </div>

        <div className="refresh">
          <div>{refreshChartBtn()}</div>
        </div>
      </div>
    );
  }

  function renderErrors() {
    const errorObj = () => {
      return (
        <h4>
          <span>{chartError.error.msg}</span>
          <span className="icon">
            <FontAwesomeIcon className="fa-fw" icon={faExclamationTriangle} />
          </span>
        </h4>
      );
    };
    return (
      <div className="errors">
        <span>{petitionNotFound && redirectPetition404(petition_id)}</span>
        <span>{chartError.status ? errorObj() : ""}</span>
      </div>
    );
  }

  return (
    <div className="Petition">
      {renderPetitionAction()}

      <div className="signatures-heading">
        <span className="icon">
          <FontAwesomeIcon className="fa-fw" icon={faPencilAlt} />
        </span>
        <h3>{lazyIntToCommaString(petition.signatures)} signatures</h3>
      </div>

      <section>
        {renderProgressBars()}
        {renderPetitionText()}
        {renderMetaSection()}
      </section>

      <div className="chart__error">{renderErrors()}</div>

      <div className="petition__chart">
        <div className="chart__time">
          <TimeNav
            timeChangeHandler={handleChartTimeChange}
            timeConfig={timeNavConfig()}
            fromNavValue={chartTime.from}
            toNavValue={getChartTimeTo()}
            presetTimeOpts={presetTimeOpts}
          ></TimeNav>
        </div>
        <Chart
          datasets={chartData}
          handleDatasetDeletion={handleDelGeoSigForm}
          toggleTotalSignatures={toggleTotalSignatures}
        />
        <div className="banner">{renderChartBannerNav()}</div>
      </div>

      <div className="nav">
        <GeoNav
          geoSearchHandler={handleAddGeoSigForm}
          geoInputData={geoNavInput}
          geoSortConfig={geoNavSortConfig.current}
          geoSortHandler={handleGeoNavSortBy}
          selectedGeoConf={geoChartConfig.current}
        ></GeoNav>
      </div>
    </div>
  );
}

export default Petition;
