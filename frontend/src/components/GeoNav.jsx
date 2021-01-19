import React, { useState, useEffect, useRef } from "react";
import Autocomplete from "react-autocomplete";
import _ from "lodash";
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import { faSearch, faChevronDown, faChevronUp } from "@fortawesome/free-solid-svg-icons";

const sortOrderIcons = {
  DESC: faChevronDown,
  ASC: faChevronUp,
};

function GeoNav({
  geoSearchHandler,
  geoSortHandler,
  geoSortConfig,
  geoInputData,
  selectedGeoConf,
}) {
  const [geoToggle, setGeoToggle] = useState("constituency");
  const [searchValues, setSearchValues] = useState({ constituency: "", country: "", region: "" });

  useEffect(() => {
    console.log(searchValues);
  }, [searchValues]);

  function pluralizeGeo(type) {
    if (type.slice(-1) === "y") {
      return `${type.slice(0, -1)}ies`;
    } else if (type.slice(-1) === "n") {
      return `${type}s`;
    }
  }

  function lazyIntToCommaString(x) {
    return x ? x.toString().replace(/\B(?=(\d{3})+(?!\d))/g, ",") : "0";
  }

  function renderGeographyRadios() {
    return (
      <div>
        <form id="toggleGeographyRadios" onChange={(e) => setGeoToggle(e.target.value)}>
          {Object.keys(geoInputData).map((geo) => {
            return (
              <div className={`radio-wrapper ${geo}`} key={`radio-wrapper ${geo}`}>
                <input
                  id={`${geo}-toggle`}
                  key={`${geo}-toggle`}
                  value={geo}
                  name={"geography"}
                  type="radio"
                  checked={geoToggle === geo}
                  readOnly={true}
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
    if (geoInputData[geoToggle].length > 0) {
      let locales = geoInputData[geoToggle];
      return (
        <div className={`search__${geoToggle} search__geo`}>
          {renderSearchForm(locales, geoToggle)}
        </div>
      );
    }
  }

  function renderSearchItem(item, isHighlighted, type) {
    return (
      <div
        key={`${item.value}-${type}`}
        className={`row
              ${isHighlighted ? "hover" : ""}
              ${item.total === 0 ? "unselectable" : ""}
              ${!shouldRenderItem(item, type) ? "hidden" : ""}
            `}
      >
        <div className="name col">
          <span>{`${item.value}`}</span>
        </div>
        <div className="code col">
          <span>{item.key}</span>
        </div>
        <div className="total col">
          <span>{lazyIntToCommaString(item.total)}</span>
        </div>
      </div>
    );
  }

  function shouldRenderItem(item, geo) {
    return !selectedGeoConf[geo].find((locale) => locale.name === item.value);
  }

  function renderSearchHeading(sortConfig, headingName, colName, geo) {
    const isChecked = sortConfig.col === colName;
    let toggleToOrder = null;
    if (isChecked) {
      toggleToOrder = sortConfig.order === "ASC" ? "DESC" : "ASC";
    } else {
      toggleToOrder = colName === "total" ? "DESC" : "ASC";
    }
    const toggleFromOrder = toggleToOrder === "ASC" ? "DESC" : "ASC";

    return (
      <div className={`${headingName} heading col radio__label`}>
        <input
          id={`${headingName}-toggle`}
          name={colName}
          value={JSON.stringify({ col: colName, geo: geo, order: toggleToOrder })}
          type="radio"
          checked={isChecked}
          readOnly={true}
          onClick={(e) => geoSortHandler(e.target.value)}
        />
        <label htmlFor={`${headingName}-toggle`}>
          <h4>{_.capitalize(headingName)}</h4>

          <div className="chevron">
            <FontAwesomeIcon className="fa-fw" icon={sortOrderIcons[toggleFromOrder]} />
          </div>
        </label>
      </div>
    );
  }

  function renderSearchMenu(items, type) {
    const sortConfig = geoSortConfig[type];
    return (
      <div className="menu__wrapper" key={`${type}-${items.length}`}>
        <header>
          {renderSearchHeading(sortConfig, "name", "value", type)}
          {renderSearchHeading(sortConfig, "code", "key", type)}
          {renderSearchHeading(sortConfig, "total", "total", type)}
        </header>
        <div className={`${type} menu`} style={{}} children={items} />
      </div>
    );
  }

  function updateSearchVal(newVal, type) {
    let values = { ...searchValues };
    values[type] = newVal;
    setSearchValues(values);
  }

  function selectSearchVal(item, newVal, type) {
    if (item.total !== 0) {
      let values = { ...searchValues };
      values[type] = "";
      setSearchValues(values);
      geoSearchHandler(type, newVal);
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
          onSelect={(val, item) => selectSearchVal(item, val, type)}
          shouldItemRender={(item, value) =>
            item.value.toLowerCase().indexOf(value.toLowerCase()) > -1 ||
            item.key.toLowerCase().indexOf(value.toLowerCase()) > -1
          }
          inputProps={{ placeholder: `Search ${_.capitalize(pluralizeGeo(type))}` }}
          renderMenu={(items) => renderSearchMenu(items, type)}
          renderItem={(item, isHighlighted) => renderSearchItem(item, isHighlighted, type)}
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
