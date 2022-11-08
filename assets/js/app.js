document.addEventListener('DOMContentLoaded', () => {
    const app = Vue.createApp({
        data() {
            return {
                postcodeInput: '',
                crimeStats: null,
                nearestPostcodes: null,
                planningPerms: null,
                firstSearch: false,
                map: null,
                highCrimeRate: false,
                longitude: null,
                latitude: null,
                postcode: '',
                constituency: '',
                loading: false,
                loadingMessage: '',
                planningPermItem: null
            }
        },
        methods: {
            onInput(e) {
                this.postCodeInput = e.target.value;
            },
            async getPostcodeData(postcode, postCodeListButtonClicked) {
                console.log('calling fetch')
                console.log(postcode)
                this.loading = true;
                this.loadingMessage = 'Loading';
                this.firstSearch = false;
                const regex = new RegExp(/\s/g)
                BASE_URL =
                  "	https://gqu7rt7slb.execute-api.us-east-2.amazonaws.com/getPostcode";
                
                let res;
                if (!postCodeListButtonClicked) {
                    res = await fetch(`${BASE_URL}?postcode=${this.postcodeInput.replace(regex, '')}`)
                    
                } else {
                    res = await fetch(
                      `${BASE_URL}?postcode=${postcode.replace(
                        regex,
                        ""
                      )}`
                    ); 
                }

                if (res.status === 200) {
                  const data = await res.json();
                  console.log(data);

                  this.postcode = data.postcode;
                  this.constituency = data.constituency;

                  this.crimeStats = data.crime_stats;
                  this.planningPerms = data.planning_perms;
                  this.nearestPostcodes = data.nearest_postcodes;

                  this.longitude = data.longitude;
                  this.latitude = data.latitude;

                  this.loadingMessage = "";
                  this.firstSearch = true;
                  this.loading = false;
                } else {
                  this.loadingMessage = "No Postcode Found!";
                }
                this.postcodeInput = '';
                this.$refs.postcodeForm.reset();
            },
            initMap() {
                this.map = new google.maps.Map(document.getElementById('map'), {
                    center: { lat: 51.500149, lng: -0.12624 },
                    zoom: 8
                })
            },
            updateMap() {
                this.map.setCenter({
                  lat: this.latitude,
                  lng: this.longitude,
                  zoom: 12,
                });

                this.map.setZoom(15);

                const marker = new google.maps.Marker({
                  position: {
                    lat: this.latitude,
                    lng: this.longitude,
                    zoom: 20,
                  },
                  map: this.map,
                });
            },
            handleClick(e) {
                this.getPostcodeData(e.target.textContent, true);
            },
            showPlanningPermDetail(item) {
                this.planningPermItem = item;
            }
        },
        watch: {
            crimeStats() {
                if (this.crimeStats.length <= 5) {
                  this.highCrimeRate = false;
                } else {
                  this.highCrimeRate = true;
                }
            },
            longitude() {
                this.updateMap();
            }
        },
        mounted() {
            this.initMap()
        }
    })

    app.mount('#app');
})