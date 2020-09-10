import React, { useState, useEffect, useRef } from "react";
import axios from "axios";
import JSONPretty from "react-json-pretty";
import _ from "lodash";
import { Link, Redirect } from "react-router-dom";
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import {
  faSearch,
  faChevronDown,
  faChevronUp,
  faPencilAlt,
  faCalendarAlt,
} from "@fortawesome/free-solid-svg-icons";

import PetitionList from "./PetitionList";
import Pagination from "./Pagination";

function PetitionListController({}) {
  const [queryParams, setQueryParams] = useState(baseQuery());
  const [petitionID, setPetitionID] = useState(null);
  const [toggleValues, setToggleValues] = useState(defaultToggleValues());
  const [petitions, setPetitions] = useState({});
  const numPetitionsFound = useRef(0);
  const paginationData = useRef(null);
  const queryResult = useRef(null);
  const baseUrl = "/petitions";

  const icons = {
    DESC: faChevronDown,
    ASC: faChevronUp,
    date: faCalendarAlt,
    signatures: faPencilAlt,
  };

  function baseQuery() {
    return {
      state: "open",
      items: 20,
      order_by: { signatures: "DESC" },
    };
  }

  useEffect(() => {}, [toggleValues]);

  useEffect(() => {
    queryPetitions();
  }, []);

  useEffect(() => {
    queryPetitions();
  }, [queryParams]);

  function resetToggleValues() {
    return {
      date: { checked: false, value: "DESC" },
      signatures: { checked: false, value: "DESC" },
    };
  }

  function defaultToggleValues() {
    return {
      date: { checked: false, value: "DESC" },
      signatures: { checked: true, value: "DESC" },
    };
  }

  async function queryPetitions() {
    const params = { params: queryParams };
    try {
      let response = await axios.get(baseUrl, params);
      let data = response.data;
      queryResult.current = data;
      paginationData.current = data.meta.pages;
      if (data.petitions) {
        numPetitionsFound.current = data.meta.items.total;
        setPetitions(data.petitions);
      }
    } catch (error) {
      // handle application not reachable
      console.log("error:", error);
    }
  }

  const handlePetitionSearchForm = (event) => {
    event.preventDefault();
    const query = event.target.query.value;

    const idRegex = new RegExp("^[0-9]{4,8}$");
    if (idRegex.test(query)) {
      setPetitionID(query);
    } else {
      let params = { ...queryParams };
      params.action = query;
      setQueryParams(params);
    }
  };

  const pageChangeHandler = ({ selected }) => {
    let params = _.cloneDeep(queryParams);
    params.index = selected + 1;
    setQueryParams(params);
  };

  const handleToggle = (event) => {
    const key = event.target.name;
    let value = event.target.value;
    let currentValues = null;
    const isChecked = toggleValues[key].checked;
    if (isChecked) {
      currentValues = _.cloneDeep(toggleValues);
      value = value == "ASC" ? "DESC" : "ASC";
      currentValues[key].value = value;
    } else {
      currentValues = resetToggleValues();
      currentValues[key].checked = true;
      currentValues[key].value = value;
    }
    currentValues[key].checked = true;
    setToggleValues(currentValues);
    let currQueryParams = _.cloneDeep(queryParams);
    currQueryParams.order_by = {};
    currQueryParams.order_by[key] = value;
    setQueryParams(currQueryParams);
  };

  function renderRadioToggle(key) {
    let radio = toggleValues[key];
    const displayValue = radio.value === "ASC" ? "DESC" : "ASC";
    return (
      <div className="radio__label">
        <input
          id={`${key}-toggle`}
          value={radio.value}
          name={key}
          type="radio"
          checked={radio.checked}
          onClick={handleToggle}
        />
        <label htmlFor={`${key}-toggle`}>
          <h4>{key}</h4>{" "}
          <div className="icon">
            <FontAwesomeIcon icon={icons[key]} />
          </div>
          <div className="chevron">
            <FontAwesomeIcon icon={icons[displayValue]} />
          </div>
        </label>
      </div>
    );
  }

  function renderToggles() {
    return (
      <div class="toggles">
        <ul>
          <li>
            <div>{renderRadioToggle("date")}</div>
          </li>
          <li>
            <div>{renderRadioToggle("signatures")}</div>
          </li>
        </ul>
      </div>
    );
  }

  function redirectIfPetitionID() {
    return petitionID ? <Redirect push to={`/petition/${petitionID}`}></Redirect> : null;
  }

  function renderSearchBar() {
    return (
      <div class="searchBar">
        <input type="text" name="query" placeholder="Search Petitions..."></input>
        <button type="submit" value="Submit">
          {" "}
          <FontAwesomeIcon icon={faSearch} />
        </button>
      </div>
    );
  }

  return (
    <div>
      {redirectIfPetitionID()}

      <div className="PetitionListController">
        <nav>
          <form onSubmit={handlePetitionSearchForm}>{renderSearchBar()}</form>
          {renderToggles()}
        </nav>

        <div className="meta">
          <h5>
            {numPetitionsFound.current} petitions {queryParams.action ? "found" : ""}
          </h5>
        </div>

        <PetitionList petitions={petitions}></PetitionList>
      </div>

      <Pagination
        pages={paginationData.current}
        baseUrl={baseUrl}
        urlParams={queryParams}
        pagesToShow={5}
        pageChangeHandler={pageChangeHandler}
      ></Pagination>
    </div>
  );
}

export default PetitionListController;
