export const getWeatherFromCityName = async (city, apiKey) => {
    const response = await fetch(`https://api.weatherapi.com/v1/current.json?q=${city}&key=${apiKey}`)
    const text = await response.text();  // or use .json() for JSON data
    const data = JSON.parse(text);
    console.log("get Weather response", data);
    if (response.status === 200) {
        return data.current.temp_c + " degree Celsius"
    } else if (response.status === 1002) {
        return "Cannot get the weather details for " + city;
    } else if (response.status === 1006) {
        return "No matching location found. Cannot get the weather details for " + city;
    } else {
        return "Failed to fetch weather data";
    }
}