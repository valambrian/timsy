from .utils import timestamp_string


class SummaryRecord:
    def __init__(self, id, description, places_lookup):
        self.id = id
        self.description = description
        self.places_lookup = places_lookup
        self.seconds = [0] * len(places_lookup)

    def add(self, place, seconds):
        index = self.places_lookup[place]
        self.seconds[index] += seconds

    def get_times(self):
        results = []
        total = 0
        for index in range(len(self.seconds)):
            current = self.seconds[index]
            total += current
            results.append(timestamp_string(current))
        results.append(timestamp_string(total))
        return results


class DailyBreakdownSummaryRecord:
    def __init__(self, id, description, dates_lookup, places_lookup):
        self.id = id
        self.description = description
        self.dates_lookup = dates_lookup
        self.places_lookup = places_lookup
        self.seconds_per_date = [0] * len(dates_lookup)
        self.seconds_per_place = [0] * len(places_lookup)

    def add(self, date, place, seconds):
        index = self.dates_lookup[date]
        self.seconds_per_date[index] += seconds
        index = self.places_lookup[place]
        self.seconds_per_place[index] += seconds

    def get_times(self):
        results = []
        total = 0
        for index in range(len(self.seconds_per_date)):
            current = self.seconds_per_date[index]
            total += current
            results.append(timestamp_string(current))
        for index in range(len(self.seconds_per_place)):
            current = self.seconds_per_place[index]
            results.append(timestamp_string(current))
        results.append(timestamp_string(total))
        return results
