import React, { useState, useEffect, useRef } from "react";
import _ from "lodash";
import ConstituenciesJSON from "../geographies/json/constituencies.json";
import RegionsJSON from "../geographies/json/regions.json";
import CountriesJSON from "../geographies/json/countries.json";
import Autocomplete from "react-autocomplete";

function GeoNav({ geoSearchHandler, geoDeleteHandler, geoConfig }) {
  const Geographies = {
    constituency: ConstituenciesJSON,
    country: CountriesJSON,
    region: RegionsJSON,
  };

  const [geoOpt, setGeoOpt] = useState(null);
  const [searchValues, setSearchValues] = useState({ constituency: "", country: "", region: "" });

  useEffect(() => {
    console.log(searchValues);
  }, [searchValues]);

  function renderLocaleDropdown() {
    if (geoOpt) {
      return (
        <div>
          <div>
            <select name={"locale"}>
              {Object.entries(Geographies[geoOpt]).map(([key, value]) => {
                console.log(`${key}:${value}`);
                return (
                  <option key={key} value={value}>
                    {`${value} (${key})`}
                  </option>
                );
              })}
            </select>
          </div>
        </div>
      );
    } else {
      return (
        <div>
          <select disabled={true} selected={true}>
            <option value="">Locale</option>
          </select>
        </div>
      );
    }
  }

  function renderGeoSearchForm() {
    if (geoSearchHandler) {
      return (
        <div className="geoSearchForm">
          <form onSubmit={geoSearchHandler}>
            <div>
              <label htmlFor={"geography"}>View Signatures By: &nbsp;</label>
              <div>
                <select
                  name={"geography"}
                  onChange={(e) => {
                    setGeoOpt(e.target.value);
                  }}
                >
                  {" "}
                  <option disabled selected value>
                    {" "}
                    -- select an option --{" "}
                  </option>
                  {Object.keys(Geographies).map((geo) => {
                    return (
                      <option key={geo} value={geo}>
                        {geo}
                      </option>
                    );
                  })}
                </select>
              </div>
            </div>
            <div>{renderLocaleDropdown()}</div>
            <button type="submit" disabled={!geoOpt}>
              Add
            </button>
          </form>
        </div>
      );
    }
  }

  function renderGeoDeleteForm() {
    if (geoDeleteHandler && geoConfig) {
      return (
        <div>
          <form className="geoDeleteForm">
            {Object.keys(geoConfig).map((geo) => {
              return (
                <div key={`${geo}-form`}>
                  <h2>{geo}</h2>
                  {/* Needs to map from object or use values inside loop */}
                  {geoConfig[geo].map((data) => {
                    let locale = data.name;
                    return (
                      <div key={`${geo}-${locale}-cb`}>
                        <label htmlFor={`${geo}-${locale}-cb`}>
                          {locale} ({data.code}) - {data.count} &nbsp;
                        </label>
                        <input
                          id={`${geo}-${locale}-cb`}
                          value={JSON.stringify({
                            geography: geo,
                            locale: locale,
                          })}
                          name={locale}
                          type="checkbox"
                          checked={true}
                          onChange={geoDeleteHandler}
                        />
                      </div>
                    );
                  })}
                </div>
              );
            })}
          </form>
        </div>
      );
    }
  }

  function createItemSearchArray(obj, type) {
    return Object.entries(obj).map((entry) => {
      return {
        key: entry[0],
        value: entry[1],
        type: type,
      };
    });
  }

  function renderGeoSearchForms() {
    return Object.entries(Geographies).map((obj) => {
      const geo = obj[0];
      let locales = obj[1];
      locales = createItemSearchArray(locales, geo);
      return <div className={`search__${geo} search__geo`}>{renderSearchForm(locales, geo)}</div>;
    });
  }

  function updateSearchVal(newVal, type) {
    let values = { ...searchValues };
    values[type] = newVal;
    setSearchValues(values);
  }

  function selectSearchVal(newVal, type) {
    let values = { ...searchValues };
    values[type] = "";
    setSearchValues(values);
    geoSearchHandler(type, newVal);
  }

  function renderSearchItem(item, isHighlighted, type) {
    return (
      <div className={`row ${isHighlighted ? "hover" : ""}`}>
        <div className="name col">
          <span>{`${item.value}`}</span>
        </div>
        <div className="total col">
          <span>{"5000"}</span>
        </div>
      </div>
    );
  }

  function renderSearchMenu(items, type) {
    return (
      <div>
        <header>
          <div className="name heading">
            <h4>Name</h4>
          </div>
          <div className="code heading">
            <h4>Code</h4>
          </div>
          <div className="total heading">
            <h4>Total</h4>
          </div>
        </header>
        <div className={`${type} menu`} style={{}} children={items} />
      </div>
    );
  }

  function pluralizeGeo(type) {
    if (type.slice(-1) === "y") {
      return `${type.slice(0, -1)}ies`;
    } else if (type.slice(-1) === "n") {
      return `${type}s`;
    }
  }

  function renderSearchForm(items, type) {
    const value = { ...searchValues }[type];
    return (
      <Autocomplete
        getItemValue={(item) => item.value}
        Heading
        items={items}
        onChange={(e) => updateSearchVal(e.target.value, type)}
        onSelect={(val) => selectSearchVal(val, type)}
        shouldItemRender={(item, value) =>
          item.value.toLowerCase().indexOf(value.toLowerCase()) > -1 ||
          item.key.toLowerCase().indexOf(value.toLowerCase()) > -1
        }
        inputProps={{ placeholder: `Search ${pluralizeGeo(type)}` }}
        renderMenu={(items) => renderSearchMenu(items, type)}
        renderItem={(item, isHighlighted) => renderSearchItem(item, isHighlighted)}
        value={value}
        Autocomplete={true}
        open={true}
        wrapperStyle={{}}
        menuStyle={{}}
      />
    );
  }

  return (
    <div className="GeoNav">
      <div className="search__forms">{renderGeoSearchForms()}</div>
      {/* <div>{renderGeoSearchForm()}</div>
      <div>{renderGeoDeleteForm()}</div> */}
    </div>
  );
}

export default GeoNav;
