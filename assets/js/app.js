document.addEventListener('DOMContentLoaded', () => {
    const app = Vue.createApp({
        data() {
            return {
                message: 'Hello World!',
                postcodeInput: '',
                crimeStats: null,
                nearestPostcodes: null,
                planningPerms: null,
                firstSearch: false
            }
        },
        methods: {
            onInput(e) {
                this.postCodeInput = e.target.value;
            },
            async getPostcodeData() {

                const regex = new RegExp(/\s/g)
                
                console.log(this.postcodeInput.replace(regex, ''));
                BASE_URL =
                  "	https://gqu7rt7slb.execute-api.us-east-2.amazonaws.com/getPostcode";
                const res = await fetch(`${BASE_URL}?postcode=${this.postcodeInput.replace(regex, '')}`)
                if (res.status === 200) {
                    const data = await res.json();
                    console.log(data)
                    const crimeStats = data.crime_stats;
                    const planningPerms = data.planning_perms;
                    const nearestPostcodes = data.nearest_postcodes;

                    this.crimeStats = crimeStats;
                    this.planningPerms = planningPerms;
                    this.nearestPostcodes = nearestPostcodes;

                    this.firstSearch = true;
                }
            }
        },
        watch: {
            postCodeInput() {
                this.getPostcodeData()
            }
        }
    })

    app.mount('#app');
})