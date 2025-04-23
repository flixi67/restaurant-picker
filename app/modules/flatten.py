import re
import pandas as pd

class FlattenPlacesResponse:
    def __init__(self, full_scope, scope=[], opening_hour_paths=[r".*OpeningHours\.periods"]):
        self.full_scope = full_scope
        self.scope = scope
        self.opening_hour_paths = opening_hour_paths

    def flatten(self, json):
        """
        Flattens response from Google Places API (new) from JSON to tabular data.
        
        Args:
            json (json): API response in JSON format.
            full_scope (boolean): True for all variables in JSON, or False
            scope (list of strings): list of key paths to the variables wanted. e.g. regularOpeningHours.weekdayDescriptions
            opening_hour_paths (regex): Regex expression matching the key paths for parsing of Google Places API opening hours.
        
        Returns:
            pandas.DataFrame: Contains all values.
        """
        if not isinstance(json, dict):
            raise ValueError("Input must be a dictionary (parsed JSON).")

        places = json.get("places", [])
        if not isinstance(places, list):
            raise ValueError("JSON must contain a 'places' list.")

        flattened_data = []
        for place in places:
            flat = self._flatten_dict(place)

            if self.full_scope:
                flattened_data.append(flat)
            elif self.scope:
                selected = {}
                for path in self.scope:
                    if path not in flat:
                        raise KeyError(f"Key path '{path}' not found in JSON object.")
                    selected[path] = flat[path]
                flattened_data.append(selected)
            else:
                raise ValueError(
                    "Either full_scope=True or a valid scope list must be provided."
                )

        return pd.DataFrame(flattened_data)

    def _flatten_dict(self, d, parent_key='', sep='.'):
        """
        Recursively flattens a nested dictionary.
        Lists of primitives are preserved. Lists of dicts are flattened.
        Special key paths are handled using custom logic.
        """
        items = []

        # Handle special case for custom paths
        if self._matches_special_path(parent_key):
            if isinstance(d, list):
                custom_value = self._parse_opening_periods(d)
                items.append((parent_key, custom_value))
                return dict(items)

        if isinstance(d, list):
            if all(isinstance(i, (str, int, float, bool, type(None))) for i in d):
                items.append((parent_key, d))
            else:
                for i, item in enumerate(d):
                    items.extend(self._flatten_dict(item, f"{parent_key}[{i}]", sep=sep).items())

        elif isinstance(d, dict):
            for k, v in d.items():
                new_key = f"{parent_key}{sep}{k}" if parent_key else k
                items.extend(self._flatten_dict(v, new_key, sep=sep).items())

        else:
            items.append((parent_key, d))

        return dict(items)

    def _matches_special_path(self, key_path):
        for pattern in self.opening_hour_paths:
            if re.fullmatch(pattern, key_path):
                return True
        return False

    def _parse_opening_periods(self, periods):
        # Converts periods to readable weekly time blocks
        day_map = ["Sunday", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"]
        result = []
        for p in periods:
            o, c = p.get("open", {}), p.get("close", {})
            try:
                open_day = day_map[o["day"]]
                close_day = day_map[c["day"]]
                open_time = f"{o['hour']:02}:{o['minute']:02}"
                close_time = f"{c['hour']:02}:{c['minute']:02}"
                result.append(f"[{open_day}: {open_time}, {close_day}: {close_time}]")
            except (KeyError, IndexError, TypeError):
                result.append("Invalid period")
        return result
        