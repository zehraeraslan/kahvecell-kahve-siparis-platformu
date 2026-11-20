export const KIZILAY = [39.9208, 32.8541]

const EARTH_RADIUS_KM = 6371

export function distanceInKilometers([latitudeA, longitudeA], [latitudeB, longitudeB]) {
  const toRadians = (degrees) => (degrees * Math.PI) / 180
  const latitudeDelta = toRadians(latitudeB - latitudeA)
  const longitudeDelta = toRadians(longitudeB - longitudeA)
  const haversine =
    Math.sin(latitudeDelta / 2) ** 2 +
    Math.cos(toRadians(latitudeA)) *
      Math.cos(toRadians(latitudeB)) *
      Math.sin(longitudeDelta / 2) ** 2

  return 2 * EARTH_RADIUS_KM * Math.asin(Math.sqrt(haversine))
}
