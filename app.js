let map;
let userMarker;

document.addEventListener('DOMContentLoaded', () => {
    // Initialize map
    map = L.map('map').setView([0, 0], 13);
    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
        attribution: '© OpenStreetMap contributors'
    }).addTo(map);

    document.getElementById('locate-me').addEventListener('click', findNearbyParking);
});

function findNearbyParking() {
    if (!navigator.geolocation) {
        alert('Geolocation is not supported by your browser');
        return;
    }

    navigator.geolocation.getCurrentPosition(position => {
        const { latitude, longitude } = position.coords;
        
        // Center map on user location
        map.setView([latitude, longitude], 15);
        
        // Add user marker
        if (userMarker) {
            userMarker.setLatLng([latitude, longitude]);
        } else {
            userMarker = L.marker([latitude, longitude]).addTo(map)
                .bindPopup('You are here')
                .openPopup();
        }

        // Search for parking using Overpass API
        searchNearbyParking(latitude, longitude);
    }, error => {
        alert('Error getting your location: ' + error.message);
    });
}

async function searchNearbyParking(lat, lon) {
    const radius = 1000; // 1km radius
    const query = `
        [out:json][timeout:25];
        (
            node["amenity"="parking"](around:${radius},${lat},${lon});
            way["amenity"="parking"](around:${radius},${lat},${lon});
        );
        out body;
        >;
        out skel qt;
    `;

    try {
        const response = await fetch('https://overpass-api.de/api/interpreter', {
            method: 'POST',
            body: query
        });
        const data = await response.json();
        
        data.elements.forEach(element => {
            if (element.lat && element.lon) {
                L.marker([element.lat, element.lon]).addTo(map)
                    .bindPopup('Parking Available');
            }
        });
    } catch (error) {
        console.error('Error fetching parking data:', error);
    }
}
