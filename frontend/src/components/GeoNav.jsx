import React, { useState, useEffect, useRef } from "react";
import ConstituenciesJSON from "../geographies/json/constituencies.json";
import RegionsJSON from "../geographies/json/regions.json";
import CountriesJSON from "../geographies/json/countries.json";

function GeoNav({ GeoSearchHandler, geoDeleteHandler, geoConfig }) {
  const Geographies = {
    constituency: ConstituenciesJSON,
    country: CountriesJSON,
    region: RegionsJSON,
  };

  const [geoOpt, setGeoOpt] = useState(null);

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
    if (GeoSearchHandler) {
      return (
        <div className="geoSearchForm">
          <form onSubmit={GeoSearchHandler}>
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

  return (
    <div className="GeoNav">
      <div>{renderGeoSearchForm()}</div>
      <div>{renderGeoDeleteForm()}</div>
    </div>
  );
}

export default GeoNav;
