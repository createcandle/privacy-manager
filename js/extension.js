(function() {
    class PrivacyManager extends window.Extension {
        constructor() {
            super('privacy-manager');
            //console.log("Adding privacy manager to menu");
            this.addMenuEntry('Privacy Manager');

            this.content = '';
            this.thing_title_lookup_table = [];

            this.min_time = new Date().getTime(); // Can only go down from here
            this.max_time = new Date(0); // Can only go up from here

            API.getThings().then((things) => {
                for (let key in things) {
                    var thing_id = things[key]['href'].substr(things[key]['href'].lastIndexOf('/') + 1);
                    this.thing_title_lookup_table[thing_id] = things[key]['title'];
                }
            });

            var latest_property_id = 4;

            fetch(`/extensions/${this.id}/views/content.html`)
                .then((res) => res.text())
                .then((text) => {
                    this.content = text;
                    if (document.location.href.endsWith("privacy-manager")) {
                        this.show();
                    }
                })
                .catch((e) => console.error('Failed to fetch content:', e));
        }


        create_thing_list(logs_list) {
            console.log("Creating main thing list");

            const pre = document.getElementById('extension-privacy-manager-response-data');
            const thing_list = document.getElementById('extension-privacy-manager-thing-list');
            thing_list.innerHTML = "";

            for (var key in logs_list) {
                console.log(key);
                var dataline = JSON.parse(logs_list[key]['name']);
                //console.log(Object.keys(dataline));

                var this_object = this;
                //console.log(this_object);

                var node = document.createElement("LI"); // Create a <li> node
                node.setAttribute("data-property-id", logs_list[key]['id']);
                node.setAttribute("data-data-type", logs_list[key]['data_type']);
                var human_readable_thing_title = dataline['thing'];
                if (human_readable_thing_title in this.thing_title_lookup_table) {
                    human_readable_thing_title = this.thing_title_lookup_table[human_readable_thing_title];
                }
                var textnode = document.createTextNode(human_readable_thing_title + ' - ' + dataline['property']); // Create a text node
                node.onclick = function() {
                    this_object.thing_list_click(this)
                };
                node.appendChild(textnode);
                thing_list.appendChild(node);
            }
            pre.innerText = "";
        }



        display_thing_data(property_id, data_type, raw_data) { // Uses json to generate dataviz
            const dataviz = document.getElementById('extension-privacy-manager-thing-dataviz');
            dataviz.innerHTML = "";
            
            var data = []

            for (var key in raw_data) {
                data.push({
                    'date': raw_data[key]['date'],
                    'value': raw_data[key]['value']
                });
            }

            var elem = document.getElementById("extension-privacy-manager-thing-dataviz-svg > *");
            if (elem != null) {
                elem.parentNode.removeChild(elem);
            }


            //var svg = d3.select("#extension-privacy-manager-thing-dataviz").append("svg"),
            var svg = d3.select("#extension-privacy-manager-thing-dataviz-svg"),
                margin = {
                    top: 20,
                    right: 20,
                    bottom: 110,
                    left: 40
                },
                margin2 = {
                    top: 430,
                    right: 20,
                    bottom: 30,
                    left: 40
                },
                width = +svg.attr("width") - margin.left - margin.right,
                height = +svg.attr("height") - margin.top - margin.bottom,
                height2 = +svg.attr("height") - margin2.top - margin2.bottom;


            svg.selectAll("*").remove();

            var date_array = [];
            var value_array = [];

            data.forEach(function(arrayItem) {
                date_array.push(new Date(arrayItem['date']));
                value_array.push(arrayItem['value']);
            });


            // Dimensions and margins
            var svg = d3.select("#extension-privacy-manager-thing-dataviz-svg");

            //var width = +svg.attr("width")
            var width = document.getElementById('extension-privacy-manager-thing-dataviz').offsetWidth;
            //console.log("offsetWidth = " + width);
            document.getElementById('extension-privacy-manager-thing-dataviz-svg').style.width = width + "px";
            //console.log();

            var height = +svg.attr("height")

            width = width - 50;
            height = height - 50;

            //var margin = {top: (0.1*width), right: (0.1*width), bottom: (0.1*width), left: (0.1*width)};
            //var margin = {top: 0, right: (0.1*width), bottom: (0.1*width), left: (0.1*width)};
            var margin = {
                top: 10,
                right: 0,
                bottom: 0,
                left: 50
            };

            // create a clipping region 
            svg.append("defs").append("clipPath")
                .attr("id", "clip")
                .append("rect")
                .attr("width", width)
                .attr("height", height);

            // Give the data a bit more space at the top and bottom
            var extra_low = d3.min(value_array) - 1;
            var extra_high = d3.max(value_array) + 1;

            // Check if the minimum and maximum date range has changed/expanded. This is used when deleting data.
            var minimum_time = d3.min(date_array)
            var maximum_time = d3.max(date_array)

            if (minimum_time < this.min_time) {
                this.min_time = minimum_time;
            }
            if (maximum_time > this.max_time) {
                this.max_time = maximum_time;
            }

            // create scale objects
            var xScale = d3.scaleTime()
                //.domain(d3.extent(date_array))
                .domain([minimum_time, maximum_time])
                .range([0, width]);
            var yScale = d3.scaleLinear()
                //.domain(d3.extent(value_array))
                .domain([d3.min(value_array) - 1, d3.max(value_array) + 1])
                .range([height, 0]);

            // create axes
            var xAxis = d3.axisBottom(xScale);
            //.ticks(20, "s");


            var yAxis = d3.axisLeft(yScale)
                .ticks(20, "s");

            // Draw Axis
            var gX = svg.append('g')
                .attr('transform', 'translate(' + margin.left + ',' + (margin.top + height) + ')')
                .call(xAxis);
            var gY = svg.append('g')
                .attr('transform', 'translate(' + margin.left + ',' + margin.top + ')')
                .call(yAxis);

            // Rectangle for the zoom function
            var rectangle_overlay = svg.append("rect")
                .attr("width", width)
                .attr("height", height)
                .style("fill", "none")
                .style("pointer-events", "all")
                .attr('transform', 'translate(' + margin.left + ',' + margin.top + ')')
            //rectangle_overlay.call(zoom);

            // Create datapoints holder
            var points_g = svg.append("g")
                .attr('transform', 'translate(' + margin.left + ',' + margin.top + ')')
                .attr("clip-path", "url(#clip)")
                .classed("points_g", true);


            // Draw Datapoints
            var points = points_g.selectAll("circle").data(data);

            points = points.enter().append("circle")
                .attr('cx', function(d) {
                    return xScale(new Date(d.date))
                })
                .attr('cy', function(d) {
                    return yScale(d.value)
                })
                .attr('r', 5)
                .style("fill-opacity", .5)
                .attr('class', 'extension-privacy-manager-svg-circle')
                .attr("data-value", function(d) {
                    return d.value;
                })
                .attr("data-date", function(d) {
                    return d.date;
                })
                .attr("data-property-id", property_id)
                .attr("data-data-type", data_type);

            // Points mouse events
            points_g.selectAll("circle")
                .on("mouseover", function(d) {
                    //console.log(this);
                    this.setAttribute('fill-opacity', 1);
                    this.setAttribute('r', 7);
                })
                .on("mouseout", function(d) {
                    //console.log(this);	
                    this.setAttribute('fill-opacity', .5);
                    this.setAttribute('r', 5);
                })
                .on("click", function(d) {
                    //console.log(this);
                    //console.log( this.getAttribute("data-date") );
                    //console.log( this.getAttribute("data-value") );
                    //console.log( this.getAttribute("data-property-id") );
                    //console.log( this.getAttribute("data-data-type") );

                    document.getElementById('extension-privacy-manager-thing-options').style.display = 'block';

                    // reset all circle to blue
                    d3.selectAll('.extension-privacy-manager-svg-circle')
                        .style('fill', 'black');

                    d3.select(this).style("fill", "magenta");

                    document.getElementById('extension-privacy-manager-input-change-old-epoch').value = this.getAttribute("data-date");

                    var select = new Date(Number(this.getAttribute("data-date")));
                    console.log("selected point as date object = " + select);

                    document.getElementById('extension-privacy-manager-input-change-value').value = this.getAttribute("data-value");
                    document.getElementById('extension-privacy-manager-input-change-property-id').value = this.getAttribute("data-property-id");

                    document.getElementById('extension-privacy-manager-input-second').value = select.getSeconds();
                    document.getElementById('extension-privacy-manager-input-minute').value = select.getMinutes(); //select.toLocaleDateString("en-UK",{minute: '2-digit'});
                    document.getElementById('extension-privacy-manager-input-hour').value = select.getHours();
                    document.getElementById('extension-privacy-manager-input-day').value = select.getDate();
                    document.getElementById('extension-privacy-manager-input-month').value = select.getMonth();
                    document.getElementById('extension-privacy-manager-input-year').value = select.getFullYear();
                    document.getElementById('extension-privacy-manager-input-millis').value = select.getMilliseconds();
                })


            // Zooming
            var zoom = d3.zoom()
                .scaleExtent([.5, 20])
                .extent([
                    [0, 0],
                    [width, height]
                ])
                .on("zoom", zoomed);

            rectangle_overlay.call(zoom);

            function zoomed() {

                // Create new scale
                var new_xScale = d3.event.transform.rescaleX(xScale);
                var new_yScale = d3.event.transform.rescaleY(yScale);

                // Update axis
                gX.call(xAxis.scale(new_xScale));

                points.data(data)
                    .attr('cx', function(d) {
                        return new_xScale(d.date)
                    })
                    .attr('cy', function(d) {
                        return yScale(d.value)
                    })
            }

        }




        // HELPER METHODS

        hasClass(ele, cls) {
            //console.log(ele);
            //console.log(cls);
            return !!ele.className.match(new RegExp('(\\s|^)' + cls + '(\\s|$)'));
        }

        addClass(ele, cls) {
            if (!this.hasClass(ele, cls)) ele.className += " " + cls;
        }

        removeClass(ele, cls) {
            if (this.hasClass(ele, cls)) {
                var reg = new RegExp('(\\s|^)' + cls + '(\\s|$)');
                ele.className = ele.className.replace(reg, ' ');
            }
        }


        thing_list_click(the_target) {
            const pre = document.getElementById('extension-privacy-manager-response-data');

            // Update CSS
            var remove_click_css_list = document.querySelectorAll('#extension-privacy-manager-thing-list > *');
            for (var i = 0, max = remove_click_css_list.length; i < max; i++) {
                this.removeClass(remove_click_css_list[i], "clicked");
            }
            this.addClass(the_target, "clicked");

            var target_property_id = the_target.getAttribute('data-property-id');
            var target_data_type = the_target.getAttribute('data-data-type');
            //console.log(target_data_type);
            document.getElementById('extension-privacy-manager-input-change-data-type').value = target_data_type; // Make sure this is always populated with the correct data type. Bit of a clumsy use of hidden fields, should improve later.
            //console.log(target_thing_id);

            // Get data for selected thing
            window.API.postJson(
                `/extensions/${this.id}/api/get_property_data`, {
                    'property_id': target_property_id,
                    'data_type': target_data_type
                }
            ).then((body) => {
                this.display_thing_data(target_property_id, target_data_type, body['data']);
                //pre.innerText = JSON.stringify(body, null, 2);
                //pre.innerText = body['state'];
            }).catch((e) => {
                console.log("Privacy manager: error getting property data");
                pre.innerText = e.toString();
            });

        }


        show() {
            if (this.content == '') {
                return;
            } else {
                this.view.innerHTML = this.content;
            }

            const pre = document.getElementById('extension-privacy-manager-response-data');
            const thing_list = document.getElementById('extension-privacy-manager-thing-list');
            const dataviz = document.getElementById('extension-privacy-manager-thing-dataviz');

            const tab_button_sculptor = document.getElementById('extension-privacy-manager-tab-button-data-sculptor');
            const tab_button_internal = document.getElementById('extension-privacy-manager-tab-button-internal-logs');
            const tab_button_quick = document.getElementById('extension-privacy-manager-tab-button-beauty-filters');
            const tab_button_print = document.getElementById('extension-privacy-manager-tab-button-print');
            const tab_button_help = document.getElementById('extension-privacy-manager-tab-button-help');

            const tab_sculptor = document.getElementById('extension-privacy-manager-tab-data-sculptor');
            const tab_internal = document.getElementById('extension-privacy-manager-tab-internal-logs');
            const tab_quick = document.getElementById('extension-privacy-manager-tab-beauty-filters');
            const tab_print = document.getElementById('extension-privacy-manager-tab-print');
            const tab_help = document.getElementById('extension-privacy-manager-tab-help');

            const button_change_point = document.getElementById('extension-privacy-manager-button-change-point');
            const button_create_point = document.getElementById('extension-privacy-manager-button-create-point');
            const button_delete_point = document.getElementById('extension-privacy-manager-button-delete-point');
            const button_delete_before = document.getElementById('extension-privacy-manager-button-delete-before');
            const button_delete_after = document.getElementById('extension-privacy-manager-button-delete-after');

            const input_change_value = document.getElementById('extension-privacy-manager-input-change-value');
            const input_change_property_id = document.getElementById('extension-privacy-manager-input-change-property-id');
            const input_change_data_type = document.getElementById('extension-privacy-manager-input-change-data-type');

            const quick_delete_button = document.getElementById('extension-privacy-manager-quick-delete-button');
            
            const bluetooth_scan_button = document.getElementById('extension-privacy-manager-start-bluetooth-scan-button');

            pre.innerText = "";



            // TABS

            document.getElementById('extension-privacy-manager-tab-buttons-container').addEventListener('click', (event) => {
                var active_tab = event.target.innerText.toLowerCase().replace(/\s/g , "-");
                console.log(active_tab);
                if(event.target.classList[0] == "extension-privacy-manager-main-tab-button"){
                    console.log("clicked on menu tab button");
                    if(active_tab == "?"){active_tab = "help";}
                    document.getElementById('extension-privacy-manager-content').className = 'extension-privacy-manager-active-tab-' + active_tab;
                }
            });
            

            
            // Print
            tab_button_print.addEventListener('click', (target) => {
                console.log("showing print tab and calling printer_init");
                //this.scan_for_printer();
                this.show_printer_state();
                /*
                window.API.postJson(
                    `/extensions/${this.id}/api/printer_init` //,{'init':1}

                ).then((body) => {
                    console.log(body);
                    //thing_list.innerText = body['data'];
                    //this.create_thing_list(body['logs']);
                    //this.create_printer_ui(body);

                }).catch((e) => {
                    //pre.innerText = e.toString();
                    console.log("Privacy manager: error in show function");
                    console.log(e.toString());
                });
                */
                
            });
            /*
            
            // Quick templates
            tab_button_quick.addEventListener('click', () => {
                this.addClass(tab_button_quick, "extension-privacy-manager-button-active");
                this.removeClass(tab_button_internal, "extension-privacy-manager-button-active");
                this.removeClass(tab_button_sculptor, "extension-privacy-manager-button-active");
                
                this.addClass(tab_internal, "extension-privacy-manager-hidden");
                this.addClass(tab_sculptor, "extension-privacy-manager-hidden");
                this.removeClass(tab_quick, "extension-privacy-manager-hidden");
            });
            */
            // Data sculptor
            tab_button_sculptor.addEventListener('click', () => {
                /*
                this.addClass(tab_button_sculptor, "extension-privacy-manager-button-active");
                this.removeClass(tab_button_internal, "extension-privacy-manager-button-active");
                this.removeClass(tab_button_quick, "extension-privacy-manager-button-active");

                this.addClass(tab_internal, "extension-privacy-manager-hidden");
                this.addClass(tab_quick, "extension-privacy-manager-hidden");
                this.removeClass(tab_sculptor, "extension-privacy-manager-hidden");
                */
                
                this.init_data_sculptor();
                
            });
            
            // Internal logs tab
            tab_button_internal.addEventListener('click', () => {
                /*
                this.addClass(tab_button_internal, "extension-privacy-manager-button-active");
                this.removeClass(tab_button_sculptor, "extension-privacy-manager-button-active");
                this.removeClass(tab_button_quick, "extension-privacy-manager-button-active");
                
                this.addClass(tab_sculptor, "extension-privacy-manager-hidden");
                this.addClass(tab_quick, "extension-privacy-manager-hidden");
                this.removeClass(tab_internal, "extension-privacy-manager-hidden");
                */
                window.API.postJson(
                    `/extensions/${this.id}/api/internal_logs`, {
                        'action': 'get',
                        'filename': 'all'
                    }

                ).then((body) => {
                    console.log(body);
                    //thing_list.innerText = body['data'];
                    this.show_internal_logs(body['data']);

                }).catch((e) => {
                    //pre.innerText = e.toString();
                    console.log("Privacy manager: error in show function:", e);
                });

            });
            
            
            // QUICK DELETE
            
            // Quick delete button
            quick_delete_button.addEventListener('click', () => {
                console.log("quick delete button pressed");
                //this.addClass(tab_button_internal, "extension-privacy-manager-button-active");
                //this.removeClass(tab_button_sculptor, "extension-privacy-manager-button-active");
                
                //this.addClass(tab_sculptor, "extension-privacy-manager-hidden");
                //this.removeClass(tab_internal, "extension-privacy-manager-hidden");

                window.API.postJson(
                    `/extensions/${this.id}/api/ajax`, {
                        'action': 'quick_delete',
                        'duration': 30
                    }

                ).then((body) => {
                    console.log("ajax API was called succcesfully");
                    //thing_list.innerText = body['data'];
                    //this.show_internal_logs(body['data']);

                }).catch((e) => {
                    //pre.innerText = e.toString();
                    console.log("Privacy manager: error in quick delete response");
                    console.log(e.toString());
                });

            });
            
            
            
            // PRINT BUTTONS
            
            bluetooth_scan_button.addEventListener('click', (target) => {
                console.log("Bluetooth printer scan button clicked");
                this.scan_for_printer();
            });
            
            document.getElementById('extension-privacy-manager-set-print-button').addEventListener('click', (target) => {
                console.log("set print button clicked");
                this.set_print();
            });
            
            
            // printer test button
            document.getElementById('extension-privacy-manager-print-test-button').addEventListener('click', (target) => {
                console.log("printer test button clicked");
                document.getElementById('extension-privacy-manager-print-test-button').style.display = 'none';
                document.getElementById('extension-privacy-manager-print-test-progress').style.display = 'block';
                window.API.postJson(
                    `/extensions/${this.id}/api/print_test` //,{'printer_log':printer_log, 'printer_interval':printer_interval}

                ).then((body) => {
                    console.log(body);
                    if(body.print_result == false){
                        alert("Could not connect to printer. Try turning it on and off again, each time by pressing the button for two seconds.")
                    }
                    else{
                        console.log("test print was succesful");
                    }
                    document.getElementById('extension-privacy-manager-print-test-progress').style.display = 'none';
                    document.getElementById('extension-privacy-manager-print-test-button').style.display = 'block';
                }).catch((e) => {
                    console.log("Privacy manager: error in print test: ", e);
                    document.getElementById('extension-privacy-manager-print-test-progress').style.display = 'none';
                    document.getElementById('extension-privacy-manager-print-test-button').style.display = 'block';
                });
            });
            
            // print now button
            document.getElementById('extension-privacy-manager-print-now-button').addEventListener('click', (target) => {
                console.log("print now button clicked");
                if(confirm("Are you sure? This will print and then delete all existing data for this particular log.")){
                    window.API.postJson(
                        `/extensions/${this.id}/api/print_now` //,{'printer_log':printer_log, 'printer_interval':printer_interval}

                    ).then((body) => {
                        console.log(body);
                        
                        if(body.print_result.state == 'error'){
                            alert("Could not connect to printer. Try turning it on and off again, each time by pressing the button for two seconds.")
                        }
                        else{
                            console.log("test print was succesful");
                        }
                        
                    }).catch((e) => {
                        console.log("Privacy manager: error in print now: ", e);
                    });
                }
                
            });
            
            


            // CHANGE POINT
            button_change_point.addEventListener('click', () => {
                //console.log("Changing point");
                //console.log(input_change_date.value);
                this.change_handler("change");
            });


            // CREATE POINT
            button_create_point.addEventListener('click', () => {
                //console.log("Creating a new point");
                this.change_handler("create");
            });


            // DELETE POINT
            button_delete_point.addEventListener('click', () => {
                //console.log("clicked delete");
                this.delete_handler("delete-point");
            });

            // DELETE ALL BEFORE
            button_delete_before.addEventListener('click', () => {
                //console.log("clicked delete before");
                this.delete_handler("delete-before");
            });

            // DELETE ALL AFTER
            button_delete_after.addEventListener('click', () => {
                //console.log("clicked delete after");
                this.delete_handler("delete-after");
            });



            // Get list of properties for sculptor
            /*
            window.API.postJson(
                `/extensions/${this.id}/api/init` //,{'init':1}

            ).then((body) => {
                console.log(body);
                //thing_list.innerText = body['data'];
                //this.create_thing_list(body['logs']);

            }).catch((e) => {
                //pre.innerText = e.toString();
                console.log("Privacy manager: error in show function");
                console.log(e.toString());
            });
            */





            //
            // INITIALISE INTERNAL LOGS BUTTONS
            //

            // DELETE ALL INTERNAL LOGS
            document.getElementById('extension-privacy-manager-button-delete-all-logs').addEventListener('click', () => {
                //console.log("clicked delete all internal logs");
                this.delete_internal_logs("all");
            });


        }







        //
        //  DATA SCULPTOR
        //


        init_data_sculptor(){
            console.log("in init_data_sculptor");
            window.API.postJson(
                `/extensions/${this.id}/api/sculptor_init` //,{'init':1}

            ).then((body) => {
                console.log(body);
                //thing_list.innerText = body['data'];
                this.create_thing_list(body['logs']);

            }).catch((e) => {
                //pre.innerText = e.toString();
                console.log("Privacy manager: error in show function");
                console.log(e.toString());
            });
            
        }



        get_new_date() {
            var fresh_date = new Date(0);
            //console.log(fresh_date);
            fresh_date.setFullYear(document.getElementById('extension-privacy-manager-input-year').value);
            fresh_date.setMonth(document.getElementById('extension-privacy-manager-input-month').value);
            fresh_date.setDate(document.getElementById('extension-privacy-manager-input-day').value);
            fresh_date.setHours(document.getElementById('extension-privacy-manager-input-hour').value);
            fresh_date.setMinutes(document.getElementById('extension-privacy-manager-input-minute').value);
            fresh_date.setSeconds(document.getElementById('extension-privacy-manager-input-second').value);
            fresh_date.setMilliseconds(document.getElementById('extension-privacy-manager-input-millis').value);

            /*
        console.log(document.getElementById('extension-privacy-manager-input-year').value);
        console.log(document.getElementById('extension-privacy-manager-input-month').value);
        console.log(document.getElementById('extension-privacy-manager-input-day').value);
        console.log(document.getElementById('extension-privacy-manager-input-hour').value);
        console.log(document.getElementById('extension-privacy-manager-input-minute').value);
        console.log(document.getElementById('extension-privacy-manager-input-second').value);
        console.log(document.getElementById('extension-privacy-manager-input-millis').value);
        
        console.log("new date stamp: " + fresh_date.valueOf() );
        */
            return fresh_date.valueOf();
        }


        change_handler(action) {
            const pre = document.getElementById('extension-privacy-manager-response-data');

            var input_change_value = document.getElementById('extension-privacy-manager-input-change-value').value;
            var updating_property_id = document.getElementById('extension-privacy-manager-input-change-property-id').value;
            var updating_data_type = document.getElementById('extension-privacy-manager-input-change-data-type').value;
            var old_date_stamp = document.getElementById('extension-privacy-manager-input-change-old-epoch').value;
            var new_date_stamp = this.get_new_date(); // reconnect all the pieces from the dropdowns (and the hidden milliseconds value) into the new date
            /*
			console.log("____action = " + action);
      console.log("property = " + updating_property_id);
			console.log("of type = " + updating_data_type);
      console.log("old_date_stamp = " + old_date_stamp);
			console.log("new_date_stamp = " + new_date_stamp);
			*/

            if (action == "create" && old_date_stamp == new_date_stamp) {
                //console.log("Shouldn't make a new point at the same date as the old one.")
                pre.innerText = "Please change the date of the new point.";
                return
            }

            window.API.postJson(
                `/extensions/${this.id}/api/point_change_value`, {
                    'action': action,
                    'property_id': updating_property_id,
                    'data_type': updating_data_type,
                    'new_value': input_change_value,
                    'old_date': old_date_stamp,
                    'new_date': new_date_stamp,
                }
            ).then((body) => {
                //thing_list.innerText = body['data'];
                //console.log(body);  
                document.getElementById('extension-privacy-manager-input-change-old-epoch').value = new_date_stamp; // Move new timestamp into "old timestamp" role, in case the user wants to change it again immediately.
                this.display_thing_data(updating_property_id, updating_data_type, body['data']);

            }).catch((e) => {
                console.log("Privacy manager: error in change handler");
                pre.innerText = e.toString();
            });
        }



        delete_handler(action) {
            /*
			console.log("Deleting point(s). Action:");
			console.log(action);
            //console.log(input_change_date.value);
			
			console.log("min-time: " + this.min_time);
			console.log("min-time: " + this.max_time);
			*/
            const pre = document.getElementById('extension-privacy-manager-response-data');
            const options_pane = document.getElementById('extension-privacy-manager-thing-options');
            //const input_change_value = document.getElementById('extension-privacy-manager-input-change-value');

            var updating_data_type = document.getElementById('extension-privacy-manager-input-change-data-type').value;
            var updating_property_id = document.getElementById('extension-privacy-manager-input-change-property-id').value;

            // In the future users could delete a selection

            const selected_point_date = document.getElementById('extension-privacy-manager-input-change-old-epoch').value;
            if (action == "delete-point") {
                var start_date_stamp = selected_point_date
                var end_date_stamp = selected_point_date; //this.get_new_date(); // reconnect all the pieces from the dropdowns (and the hidden milliseconds value) into the new date
            } else if (action == "delete-before") {
                var start_date_stamp = this.min_time.getTime(); //toUTCString();
                var end_date_stamp = selected_point_date;
            } else if (action == "delete-after") {
                var start_date_stamp = selected_point_date
                var end_date_stamp = this.max_time.getTime(); //.toUTCString();
            }
            /*
			console.log("____action = " + action);
            console.log("property = " + updating_property_id);
			console.log("of type = " + updating_data_type);
            console.log("end_date_stamp = " + end_date_stamp);
            console.log("start_date_stamp = " + start_date_stamp);
    	    */
            options_pane.style.opacity = .5;


            window.API.postJson(
                `/extensions/${this.id}/api/point_delete`, {
                    'action': action,
                    'property_id': updating_property_id,
                    'data_type': updating_data_type,
                    'start_date': start_date_stamp,
                    'end_date': end_date_stamp
                }
            ).then((body) => {
                options_pane.style.opacity = 1;
                //console.log(body['data']);

                document.getElementById('extension-privacy-manager-input-change-old-epoch').value = "";
                document.getElementById('extension-privacy-manager-input-change-value').value = "";

                // Update the dataviz
                this.display_thing_data(updating_property_id, updating_data_type, body['data']);

            }).catch((e) => {
                console.log("Privacy manager: error in deletion handler");
                pre.innerText = e.toString();
            });

        } // End of button delete point add listener




        //
        //  INTERNAL LOGS
        //


        show_internal_logs(file_list) {

            const pre = document.getElementById('extension-privacy-manager-response-data');
            const logs_list = document.getElementById('extension-privacy-manager-logs-list');

            file_list.sort();
            //console.log(file_list)

            logs_list.innerHTML = "";

            for (var key in file_list) {

                var this_object = this;

                var node = document.createElement("LI"); // Create a <li> node
                node.setAttribute("class", "extension-privacy-manager-deletable_item");
                node.setAttribute("data-filename", file_list[key]);

                var textnode = document.createTextNode(file_list[key]); // Create a text node
                node.onclick = function() {
                    //this_object.delete_internal_logs( file_list[key] )
                    this_object.delete_internal_logs(this.getAttribute("data-filename"));
                };
                node.appendChild(textnode);

                logs_list.appendChild(node);
            }
            pre.innerText = "";
        }



        delete_internal_logs(filename) {
            //console.log("Deleting log files. filename:");
            //console.log(filename);

            const pre = document.getElementById('extension-privacy-manager-response-data');
            const logs_list = document.getElementById('extension-privacy-manager-logs-list');

            window.API.postJson(
                `/extensions/${this.id}/api/internal_logs`, {
                    'action': 'delete',
                    'filename': filename
                }

            ).then((body) => {
                //console.log(body);
                this.show_internal_logs(body['data']);

            }).catch((e) => {
                console.log("Privacy manager: error in internal log deletion handler");
                pre.innerText = e.toString();
            });

        } // End of button delete point add listener





        //
        //  BLUETOOTH PRINTER
        //

        scan_for_printer(){
            console.log("scan_for_printer was called. Calling API for /printer_scan");
            document.getElementById('extension-privacy-manager-print-busy-scanning').style.display = 'block';
            document.getElementById('extension-privacy-manager-start-bluetooth-scan-button').style.display = 'none';
            
            window.API.postJson(
                `/extensions/${this.id}/api/printer_scan` //,{'init':1}

            ).then((body) => {
                console.log(body);
                
                document.getElementById('extension-privacy-manager-printer-list-name').innerText = body['persistent']['printer_name'];
                document.getElementById('extension-privacy-manager-printer-list-mac').innerText = body['persistent']['printer_mac'];
                
                //thing_list.innerText = body['data'];
                //this.create_thing_list(body['logs']);
                //this.create_printer_ui(body, true);
                document.getElementById('extension-privacy-manager-print-busy-scanning').style.display = 'none';
                document.getElementById('extension-privacy-manager-start-bluetooth-scan-button').style.display = 'block';

            }).catch((e) => {
                //pre.innerText = e.toString();
                console.log("Privacy manager: error in show function");
                console.log(e.toString());
                document.getElementById('extension-privacy-manager-print-busy-scanning').style.display = 'none';
                document.getElementById('extension-privacy-manager-start-bluetooth-scan-button').style.display = 'block';
            });
        }


        /*
        wait_for_printer_state(){
            console.log("setting timeout to call show_printer_state in 10 seconds");
            //window.setTimeout(this.show_printer_state, 10000);
        }
        */


        show_printer_state(scanning){
            if(typeof scanning != 'undefined'){
                // show still scanning
            }
            
            window.API.postJson(
                `/extensions/${this.id}/api/printer_init` //,{'init':1}

            ).then((body) => {
                console.log(body);
                if(body.scanning){
                    console.log("still scanning");
                }
                else{
                    console.log("not currently scanning");
                }
                // if still scanning is true, also call wait_for_printer_state again (and make sure the "still scanning" message is shown)
                // if scanning is done, just remove the "still scanning" message
                document.getElementById('extension-privacy-manager-printer-list-name').innerText = body['persistent']['printer_name'];
                document.getElementById('extension-privacy-manager-printer-list-mac').innerText = body['persistent']['printer_mac'];
                
                if(body['persistent']['printer_mac'] != ""){
                    
                    document.getElementById('extension-privacy-manager-print-test-button').style.display = 'block';
                }
                
                // Clean slate - print everything
                if( typeof body['persistent']['printer_log_name'] != 'undefined'){
                    if(body['persistent']['printer_log_name'] != "None"){
                        document.getElementById('extension-privacy-manager-selected-log-to-print').innerText = body['persistent']['printer_log_name'];
                        document.getElementById('extension-privacy-manager-clean-slate-container').style.display = 'block';
                    }
                }
                
                
                
                // Interval select correct option
                if(typeof body['persistent']['printer_interval'] != 'undefined'){
                    console.log("body['printer_interval'] = " + body['persistent']['printer_interval']);
                    var interval_dropdown = document.getElementById('extension-privacy-manager-printer-interval-dropdown');
                    for (var i = 0; i < interval_dropdown.options.length; i++) {
                        if( interval_dropdown.options[i].value === body['persistent']['printer_interval'] ){
                            interval_dropdown.selectedIndex = i;
                            break;
                        }
                    }
                }
                
                // Rotation set correct option
                if(typeof body['persistent']['printer_rotation'] != 'undefined'){
                    console.log("body['printer_rotation'] = " + body['persistent']['printer_rotation']);
                    var rotation_dropdown = document.getElementById('extension-privacy-manager-printer-rotation-dropdown');
                    for (var i = 0; i < rotation_dropdown.options.length; i++) {
                        console.log(rotation_dropdown.options[i].value + " =?= " + body['persistent']['printer_rotation']);
                        if( parseInt(rotation_dropdown.options[i].value) === parseInt(body['persistent']['printer_rotation']) ){
                            console.log("correct rotation spotted");
                            rotation_dropdown.selectedIndex = i;
                            break;
                        }
                    }
                }
                
                
                
                //document.getElementById('extension-privacy-manager-printer-interval-dropdown');
                
                var log_to_print_dropdown = document.createElement("select"); 
                log_to_print_dropdown.setAttribute("id", "extension-privacy-manager-log-to-print");
                log_to_print_dropdown.setAttribute("class", "localization-select");
                
                // Add "none" option
                log_to_print_dropdown.options[log_to_print_dropdown.options.length] = new Option("None", "none");
                
                
                const logs_list = body['logs'];
                
                for (var key in logs_list) {
                    //console.log(key);
                    var dataline = JSON.parse(logs_list[key]['name']);
                    //console.log(Object.keys(dataline));

                    //var this_object = this;
                    //console.log(this_object);

                    //var node = document.createElement("LI"); // Create a <li> node
                    //node.setAttribute("data-property-id", logs_list[key]['id']);
                    //node.setAttribute("data-data-type", logs_list[key]['data_type']);
                    var human_readable_thing_title = dataline['thing'];
                    if (human_readable_thing_title in this.thing_title_lookup_table) {
                        human_readable_thing_title = this.thing_title_lookup_table[human_readable_thing_title] + ' - ' + dataline['property'];
                    }
                    //console.log(human_readable_thing_title);
                    
                    
                    var new_option = new Option(human_readable_thing_title,logs_list[key]['id']);
                    if(typeof body['persistent']['printer_log'] != 'undefined'){
                        if( body['persistent']['printer_log'] == logs_list[key]['id'] ){
                            console.log("setting selected log: " + logs_list[key]['id']);
                            new_option.selected = true;
                        }
                    }
                    
                        
                    log_to_print_dropdown.options[log_to_print_dropdown.options.length] = new_option;
                    
                    //var textnode = document.createTextNode(human_readable_thing_title + ' - ' + dataline['property']); // Create a text node
                    //node.onclick = function() {
                    //    this_object.thing_list_click(this)
                    //};
                    //node.appendChild(textnode);
                    //thing_list.appendChild(node);
                }
                
                
                /*
				for( var log in body['logs'] ){
                    console.log(log);
                    console.log(body['logs'][log]);
                    console.log(body['logs'][log]['name']);
                    let log_details = JSON.parse(body['logs'][log]['name']);
					log_to_print_dropdown.options[property_dropdown.options.length] = new Option("value", "log name");
				}
                */
                console.log( document.getElementById('extension-privacy-manager-printer-log-dropdown-container') );
                document.getElementById('extension-privacy-manager-printer-log-dropdown-container').innerHTML = "";
                document.getElementById('extension-privacy-manager-printer-log-dropdown-container').append(log_to_print_dropdown);
                
                

            }).catch((e) => {
                //pre.innerText = e.toString();
                console.log("Privacy manager: error in show_printer_state function", e);
            });
        }




        set_print(){
            console.log('in set_print');
            
            const selected_log_element = document.getElementById("extension-privacy-manager-log-to-print");
            var printer_log = selected_log_element.options[selected_log_element.selectedIndex].value;
            var printer_log_name = selected_log_element.options[selected_log_element.selectedIndex].text;
            
            const selected_log_interval_element = document.getElementById("extension-privacy-manager-printer-interval-dropdown");
            var printer_interval = selected_log_interval_element.options[selected_log_interval_element.selectedIndex].value;
            
            const selected_rotation_element = document.getElementById("extension-privacy-manager-printer-rotation-dropdown");
            var printer_rotation = selected_rotation_element.options[selected_rotation_element.selectedIndex].value;
            
            
            
            window.API.postJson(
                `/extensions/${this.id}/api/printer_set`,{'printer_log':printer_log, 'printer_interval':printer_interval, 'printer_log_name':printer_log_name, 'printer_rotation':printer_rotation}

            ).then((body) => {
                console.log(body);
                
                document.getElementById('extension-privacy-manager-printer-list-name').innerText = body['persistent']['printer_name'];
                document.getElementById('extension-privacy-manager-printer-list-mac').innerText = body['persistent']['printer_mac'];
                
                //thing_list.innerText = body['data'];
                //this.create_thing_list(body['logs']);
                //this.create_printer_ui(body, true);
                document.getElementById('extension-privacy-manager-print-busy-scanning').style.display = 'none';
                document.getElementById('extension-privacy-manager-start-bluetooth-scan-button').style.display = 'block';

            }).catch((e) => {
                //pre.innerText = e.toString();
                console.log("Privacy manager: error in show function");
                console.log(e.toString());
                document.getElementById('extension-privacy-manager-print-busy-scanning').style.display = 'none';
                document.getElementById('extension-privacy-manager-start-bluetooth-scan-button').style.display = 'block';
            });
            
        }



    }
    new PrivacyManager();

})();