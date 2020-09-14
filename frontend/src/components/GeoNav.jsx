import React, { useState, useEffect, useRef } from "react";
import _ from "lodash";
import ConstituenciesJSON from "../geographies/json/constituencies.json";
import RegionsJSON from "../geographies/json/regions.json";
import CountriesJSON from "../geographies/json/countries.json";
import Autocomplete from "react-autocomplete";

function GeoNav({ geoSearchHandler, geoInputData, geoChartConfig }) {
  const Geographies = {
    country: CountriesJSON,
    constituency: ConstituenciesJSON,
    region: RegionsJSON,
  };

  const [geoToggle, setGeoToggle] = useState("constituency");
  const [searchValues, setSearchValues] = useState({ constituency: "", country: "", region: "" });

  useEffect(() => {
    console.log(searchValues);
  }, [searchValues]);

  function renderGeographyRadios() {
    return (
      <div>
        <form id="toggleGeographyRadios" onChange={(e) => setGeoToggle(e.target.value)}>
          {Object.keys(Geographies).map((geo) => {
            return (
              <div className={`radio-wrapper ${geo}`}>
                <input
                  id={`${geo}-toggle`}
                  key={`${geo}-toggle`}
                  value={geo}
                  name={"geography"}
                  type="radio"
                  checked={geoToggle === geo}
                ></input>
                <label htmlFor={`${geo}-toggle`}>
                  <h5>{_.capitalize(geo)}</h5>
                </label>
              </div>
            );
          })}
        </form>
      </div>
    );
  }

  function renderGeographySearchForm() {
    if (geoInputData) {
      let locales = geoInputData[geoToggle];
      return (
        <div className={`search__${geoToggle} search__geo`}>
          {renderSearchForm(locales, geoToggle)}
        </div>
      );
    }
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
        <div className="code col">
          <span>{item.key}</span>
        </div>
        <div className="total col">
          <span>{item.total}</span>
        </div>
      </div>
    );
  }

  function renderSearchMenu(items, type) {
    return (
      <div className="menu__wrapper">
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
      <form id="selectLocaleForm">
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
          inputProps={{ placeholder: `Search ${_.capitalize(pluralizeGeo(type))}` }}
          renderMenu={(items) => renderSearchMenu(items, type)}
          renderItem={(item, isHighlighted) => renderSearchItem(item, isHighlighted)}
          value={value}
          Autocomplete={true}
          open={true}
          wrapperStyle={{}}
          menuStyle={{}}
        />
      </form>
    );
  }

  return (
    <div className="GeoNav">
      <div>{renderGeographyRadios()}</div>
      <div>{renderGeographySearchForm()}</div>
    </div>
  );
}

export default GeoNav;
