(function() {
    class PrivacyManager extends window.Extension {
        constructor() {
            super('privacy-manager');
            //console.log("Adding privacy manager to menu");
            this.addMenuEntry('Privacy Manager');

            this.debug = false;
            
            this.content = '';
            this.thing_title_lookup_table = [];

            this.min_time = new Date().getTime(); // Can only go down from here
            this.max_time = new Date(0); // Can only go up from here

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




    
        generate_things_overview(scene_name){
            
            document.getElementById('extension-privacy-manager-view').scrollTop = 0;
            
            let list_el = document.getElementById('extension-privacy-manager-things-list-container');
            list_el.innerHTML = "";
            var at_least_on_thing_shown = false; // how many things with settings are shown in the UI
            
    		// Pre populating the original item that will be clones to create new ones
    	    API.getThings().then((things) => {
			
                things.sort((a, b) => (a.title.toLowerCase() > b.title.toLowerCase()) ? 1 : -1) // sort alphabetically
            
    			this.all_things = things;
    			if(this.debug){
                    console.log("privacy_manager: debug: all things: ", things);
                }
			    
    			// pre-populate the hidden 'new' item with all the thing names
    			var thing_ids = [];
    			var thing_titles = [];
			
    			for (let key in things){

                    if( things[key].hasOwnProperty('properties') ){ // things without properties should be skipped (edge case)
                        
        				var thing_title = 'unknown';
        				if( things[key].hasOwnProperty('title') ){
        					thing_title = things[key]['title'];
        				}
        				else if( things[key].hasOwnProperty('label') ){ // very old addons sometimes used label instead of title
        					thing_title = things[key]['label'];
        				}
				
        				
        				
			
        				var thing_id = things[key]['href'].substr(things[key]['href'].lastIndexOf('/') + 1);
                        if(this.debug){
                            console.log("thing_id: ", thing_id);
                            console.log("thing_title: ", thing_title);
                        }
                        
                        if(thing_id == 'scenes-thing'){
                            //console.log("FOUND IT scenes-thing");
                            continue;
                        }
                        
                        if (thing_id.startsWith('highlights-') ){
    						//console.log(thing_id + " starts with highlight-, so skipping.");
    						continue;
                        }
                        
                        //console.log("thing_title and ID: ", thing_title, thing_id);
                        
                        
        				//thing_ids.push( things[key]['href'].substr(things[key]['href'].lastIndexOf('/') + 1) );

                        var thing_container = document.createElement('div');
                        thing_container.classList.add('extension-privacy-manager-things-edit-item')
                        thing_container.dataset.thing_id = thing_id;
                        
                        thing_container.setAttribute('id','extension-privacy-manager-things-' + thing_id + '-container');
                        
                        /*
                        var thing_checkbox = document.createElement('input');
                        thing_checkbox.type = "checkbox";
                        thing_checkbox.name = 'extension-privacy-manager-things-' + thing_id;
                        thing_checkbox.id = 'extension-privacy-manager-things-' + thing_id;
                        thing_checkbox.classList.add('extension-privacy-manager-things-edit-item-thing-checkbox');
                        */
                        
                        var thing_label = document.createElement('h4');
                        //thing_label.htmlFor = 'extension-privacy-manager-things-' + thing_id;
                        //label.appendChild(checkbox);
                        thing_label.appendChild(document.createTextNode(thing_title));
                
                    
                    
                        // ADD PROPERTIES CONTAINER TO THE THING CONTAINER
                    
                        var properties_container = document.createElement('div');
                        properties_container.classList.add('extension-privacy-manager-things-edit-item-properties');
                        properties_container.setAttribute('id','extension-privacy-manager-things-' + thing_id + '-properties');
                        
                        
                        thing_container.appendChild(thing_label);
                        thing_container.appendChild(properties_container);
                        
                        // Append edit view to the dom
                        document.getElementById('extension-privacy-manager-things-list-container').appendChild(thing_container);
                        
                        
                        
                        var found_write_property = false;
                        let properties = things[key]['properties'];
                		for (let prop in properties){
                			//console.log(properties[prop]);
                			var property_title = 'unknown';
                			if( properties[prop].hasOwnProperty('title') ){
                				property_title = properties[prop]['title'];
                			}
                			else if( properties[prop].hasOwnProperty('label') ){
                				property_title = properties[prop]['label'];
                			}
			
                			var property_id = properties[prop]['forms'][0]['href'].substr(properties[prop]['forms'][0]['href'].lastIndexOf('/') + 1);
                            //console.log("property_id: ", property_id);
                            
                            var read_only = false;
                            if( typeof properties[prop]['readOnly'] != 'undefined'){
                                if(properties[prop]['readOnly'] == true){
                                    read_only = true;
                                }
                            }
                            
                            if(read_only == false){
                                
                                if(property_title != 'Data collection' && property_title != 'Data mute' && property_title != 'Data blur'){
                                    continue;
                                }
                                
                                let my_thing_id = thing_id;
                                let my_property_id = property_id;
                                let my_property_title = property_title;
                                //console.log("my_thing_id early: ", my_thing_id);
                                
                                try{
                                    // get actual current value of the property
                                    API.getJson('/things/' + my_thing_id + '/properties/' + my_property_id)
                                    .then((prop2) => {
                                 
                                        if(typeof prop2 == 'object'){
                                            // gateway 1.0.0
                                            if(Object.keys(prop2).length === 0 && this.debug){
                                                console.log(property_id + " was Undefined");
                                            }
                                            else if(prop2[property_name] == null && this.debug){
                                                console.log(property_id + " WAS NULL");
                                            
                                            }
                                        }
                                        else{
                                            if(prop2 == null && this.debug){
                                                console.log(property_id + " WAS NULL: ", prop2);
                                            }
                                        
                                            let property_value = prop2; //properties[prop]['value'];
                                            if(property_value == null){
                                                property_value = 'unknown';
                                            }
                                
                                            if(this.debug){
                                                console.log("privacy manager debug: property and property_value: ", properties[prop], property_value);
                                            }
                                
                                            // Create container for property
                                            var property_container = document.createElement('div');
                                            property_container.classList.add('extension-privacy-manager-things-edit-item-property');
                                            property_container.dataset.property_id = property_id
                                
                                            // Property is part of scene checkbox
                                            /*
                                            var property_checkbox = document.createElement('input');
                                            property_checkbox.type = "checkbox";
                                            property_checkbox.name = 'extension-privacy-manager-things-' + thing_id + '---' + property_id;
                                            property_checkbox.id = 'extension-privacy-manager-things-' + thing_id + '---' + property_id;
                                            property_checkbox.classList.add('extension-privacy-manager-things-edit-item-property-checkbox');
                                            */
                                
                                
                                            // Create label for property
                                            var property_label_el = document.createElement('label');
                                            property_label_el.htmlFor = 'extension-privacy-manager-things-' + thing_id + '---' + property_id;
                                            property_label_el.appendChild(document.createTextNode(my_property_title));
                                
                                
                                
                                
                                            // Create input element for the property value
                                            var input_el = document.createElement('input');
                                            input_el.name = 'extension-privacy-manager-things-' + thing_id + '-----' + property_id;
                                            input_el.id = 'extension-privacy-manager-things-' + thing_id + '-----' + property_id;
                                            input_el.classList.add('extension-privacy-manager-things-edit-item-property-value');
                                            input_el.dataset.thing_id = thing_id;
                                            input_el.dataset.property_id = property_id;
                    			
                                            // Number property
                                			if( properties[prop]['type'] == 'integer' || properties[prop]['type'] == 'float' || properties[prop]['type'] == 'number'){
                                                // If a property is a number
                			                    //console.log("number property spotted");
                                                input_el.type = "number";
                                			}
                                
                                            // Boolean property
                                            else if( properties[prop]['type'] == 'boolean'){
                                                //console.log("boolean property spotted");
                                                input_el = document.createElement('select');
                                                input_el.name = 'extension-privacy-manager-things-' + thing_id + '-----' + property_id;
                                                input_el.id = 'extension-privacy-manager-things-' + thing_id + '-----' + property_id;
                                                input_el.classList.add('extension-privacy-manager-things-edit-item-property-value');
                                                input_el.classList.add('extension-privacy-manager-dropdown');
                                                input_el.classList.add('localization-select');
                                    
                                    
                                    
                                                input_el.dataset.thing_id = thing_id;
                                                input_el.dataset.property_id = property_id;
                                    
                                                var unknown_option = document.createElement("option");
                                                unknown_option.value = 'unknown';
                                                unknown_option.text = 'Unknown';
                                                if(property_value.toString() == unknown_option.value){
                                                    unknown_option.selected = true;
                                                }
                                                input_el.appendChild(unknown_option);
                                    
                                                var true_option = document.createElement("option");
                                                true_option.value = 'true';
                                                true_option.text = 'True';
                                                if(property_value.toString() == true_option.value){
                                                    true_option.selected = true;
                                                }
                                                input_el.appendChild(true_option);
                                    
                                                var false_option = document.createElement("option");
                                                false_option.value = 'false';
                                                false_option.text = 'False';
                                                if(property_value.toString() == false_option.value){
                                                    false_option.selected = true;
                                                }
                                                input_el.appendChild(false_option);
                                    
                                    
                                                if(at_least_on_thing_shown == false){
                                                    at_least_on_thing_shown = true;
                                                    document.getElementById('extension-privacy-manager-no-things-warning').style.display = 'none';
                                                };
                                            }
                                
                                            // Color property
                                            else if( properties[prop]['type'] == 'color'){
                                                //console.log("color property spotted");
                                                input_el.type = "color";
                                            }
                                
                                            // String property
                                            else if( properties[prop]['type'] == 'string'){
                                                //console.log("string property spotted");
                                                input_el.type = "text";
                                    
                                                if(property_id == "color"){
                                                    input_el.type = "color";
                                                }
                                    
                                                if (typeof properties[prop]['enum'] != 'undefined'){
                                                    //console.log('enum spotted');
                                        
                                                    input_el = document.createElement('select');
                                                    input_el.name = 'extension-privacy-manager-things-' + thing_id + '-----' + property_id;
                                                    input_el.id = 'extension-privacy-manager-things-' + thing_id + '-----' + property_id;
                                                    input_el.classList.add('extension-privacy-manager-things-edit-item-property-value');
                                                    input_el.classList.add('extension-privacy-manager-dropdown');
                                                    input_el.classList.add('localization-select');
                                                    input_el.dataset.thing_id = thing_id;
                                                    input_el.dataset.property_id = property_id;
                                        
                                                    for (var i = 0; i < properties[prop]['enum'].length; i++) {
                                                        var option = document.createElement("option");
                                                        option.value = properties[prop]['enum'][i];
                                                        option.text = properties[prop]['enum'][i];
                                                        if(property_value == option.value){
                                                            option.selected = true;
                                                        }
                                                        input_el.appendChild(option);
                                                    }
                                        
                                                    if(at_least_on_thing_shown == false){
                                                        at_least_on_thing_shown = true;
                                                        document.getElementById('extension-privacy-manager-no-things-warning').style.display = 'none';
                                                    };
                                        
                                                }
                                            }
                                
                                            // unsupported property
                                            else{
                                                if(this.debug){
                                                    console.log("Scenes: Warning, unsupported property type. Skipping");
                                                }
                                                //continue;
                                            }
                                
                                            // Automatically check the checkbox if the property is changed
                                            input_el.addEventListener('change', (event) => {
                    	                        if(this.debug){
                    	                            console.log("privacy manager: things: property value changed. Event: ", event);
                    	                            console.log("input_el: ", input_el);
                                                    console.log("event.target.value: ", event.target.value);
                                                }
                                    
                                    
                                                API.putJson(`/things/${my_thing_id}/properties/${my_property_id}`, event.target.value);
                                    
                                                //console.log("event.currentTarget.parentNode: ", event.currentTarget.parentNode);
                                                //const parent_el = event.currentTarget.closest('.extension-privacy-manager-things-edit-item-property');
                                                //const checkbox_sibling = parent_el.getElementsByClassName('extension-privacy-manager-things-edit-item-property-checkbox')[0];
                                                //checkbox_sibling.checked = true;
                                            });
                                
                                
                                            // Add property element to the property container
                                            //property_container.appendChild(property_checkbox);
                                            property_container.appendChild(property_label_el);
                                            property_container.appendChild(input_el);
                                
                                            document.getElementById('extension-privacy-manager-things-' + my_thing_id + '-properties').appendChild(property_container);
                                            document.getElementById('extension-privacy-manager-things-' + my_thing_id + '-container').style.display = 'block';
                                
                                
                                            // Add the property container to the thing container
                                            //properties_container.appendChild(property_container);
                                        
                                        }
                            
                            
                                    })
                                    .catch((err) => {
                                        console.log("privacy manager: generating things overview: API error getting fresh property value. Device probably not connected: ", err);
                                    });
                                    found_write_property = true;
                                }
                                catch(e){
                                    if(this.debug){
                                        console.log("Privacy manager: Error getting fresh privacy-related property value: ", e);
                                    }
                                }
                                
                                
                                
                            }
                			
                		}
                    
                        /*
                        // Add thing container to the edit overview
                        if(found_write_property){
                            //thing_container.appendChild(thing_checkbox);
                            thing_container.appendChild(thing_label);
                            thing_container.appendChild(properties_container);
                            
                            // Append edit view to the dom
                            document.getElementById('extension-privacy-manager-things-list-container').appendChild(thing_container);
                        }
                        else{
                            if(this.debug){
                                console.log('scenes:debug: thing has no writeable properties: ', thing_id);
                            }
                        }
                        */

                    }
    			}
    	    });
            
        } // end of edit_scene
    
    











        // Sculptor things list
        create_sculptor_thing_list(logs_list) {
            if(this.debug){
                console.log("privacy manager: in create_sculptor_thing_list. logs_list: ", logs_list);
            }
            
            try{
                const pre = document.getElementById('extension-privacy-manager-response-data');
                const thing_list = document.getElementById('extension-privacy-manager-thing-list');
                thing_list.innerHTML = "";

                /*
                logs_list = logs_list.sort((a, b) => {
                  return a.localeCompare(b, undefined, {sensitivity: 'base'});
                });
                */


                for (var key in logs_list) {
                    //console.log(key);
                    let dataline = JSON.parse(logs_list[key]['name']);

                    // Create the nice name string
                    const nice_name = this.get_thing_and_property_string(dataline['thing'],dataline['property']);
                    logs_list[key]['nice_name'] = nice_name;
                
                    // If the generated nicename is the same as the thing name, that indicates the device is not available.
                    if(nice_name == dataline['thing']){
                        logs_list[key]['missing'] = true;
                        logs_list[key]['nice_name'] = nice_name + " " + dataline['property'];
                    }
                    else{
                        logs_list[key]['missing'] = false;
                    }
                    //const nice_name = this.get_thing_and_property_string(dataline['thing'],dataline['property']);
                }
            
                // Sort the list
                /*
                logs_list = logs_list.sort((a, b) => {
                  return a.localeCompare(b, undefined, {sensitivity: 'base'});
                });
                */
                /*
                logs_list = new Array([...logs_list].sort(([k, v], [k2, v2])=> {
                    if(typeof v.nicename != 'undefined' && typeof v2.nicename != 'undefined'){
                        const v_nicename = v.nicename.toLowerCase();
                        const v2_nicename = v2.nicename.toLowerCase();
                        if (v_nicename > v2_nicename) {
                          return 1;
                        }
                        if (v_nicename < v2_nicename) {
                          return -1;
                        }
                        return 0;
                    }
                }));
                */
            
            
                // Sort the logs list by nice name
                function alphabetical_sort(a,b) {
                    if(typeof a.nice_name != 'undefined' && typeof b.nice_name != 'undefined'){
                        const a_nicename = a.nice_name.toLowerCase();
                        const b_nicename = b.nice_name.toLowerCase();
                        if (a_nicename > b_nicename) {
                          return 1;
                        }
                        if (a_nicename < b_nicename) {
                          return -1;
                        }
                        return 0;
                    }else{
                        console.warn('alphabetical_sort: no nicename in object');
                    }
                }
                logs_list.sort(alphabetical_sort);
                if(this.debug){
                    console.log("sorted logs list with nicenames: ", logs_list);
                }
            
                for (var key in logs_list) {
                    //console.log(key);
                    //var dataline = JSON.parse(logs_list[key]['name']);
                    //console.log(Object.keys(dataline));

                    //var this_object = this;
                    //console.log(this_object);
                
                    if(logs_list[key]['missing'] == false ){
                        var node = document.createElement("LI"); // Create a <li> node
                        node.setAttribute("data-property-id", logs_list[key]['id']);
                        node.setAttribute("data-data-type", logs_list[key]['data_type']);
                
                        /*
                        var human_readable_thing_title = dataline['thing'];
                        if (human_readable_thing_title in this.thing_title_lookup_table) {
                            human_readable_thing_title = this.thing_title_lookup_table[human_readable_thing_title];
                        }
                        */
                
                        //const nice_name = this.get_thing_and_property_string(dataline['thing'],dataline['property']);
                        //console.log("nice name: " + nice_name);
                        var textnode = document.createTextNode( logs_list[key]['nice_name']); // Create a text node
                        node.appendChild(textnode);
                
                        node.onclick = (event) => {
                            document.getElementById('extension-privacy-manager-thing-options').style.display = 'none';
                            this.thing_list_click(event.target);
                        };
                
                        thing_list.appendChild(node);
                    }
                
                
                }
                pre.innerText = "";
            }
            catch(e){
                console.log("Privacy manager: error in create_sculptor_thing_list: ", e);
            }
        }



        display_thing_data(property_id, data_type, raw_data) { // Uses json to generate dataviz
            
            try{
                //console.log("in display_thing_data. property_id: " + property_id);
                const dataviz = document.getElementById('extension-privacy-manager-thing-dataviz');
                document.getElementById("extension-privacy-manager-sculptor-loading-data").style.display = 'none';
                //console.log("dataviz:",dataviz);
                //dataviz.innerHTML = "";
            
            
                if(raw_data.length == 0){
                    //console.log("no data to visualize");
                    document.getElementById('extension-privacy-manager-no-data-available').style.display = 'block';
                    document.getElementById("extension-privacy-manager-thing-dataviz-svg").style.display = 'none';
                }
                else{
                    document.getElementById('extension-privacy-manager-no-data-available').style.display = 'none';
                    document.getElementById("extension-privacy-manager-thing-dataviz-svg").style.display = 'block';
                    /*
                    let svg_element = document.createElement("svg");  
                    svg_element.classList.add('extension-privacy-manager-thing-dataviz-svg');
                    dataviz.appendChild(svg_element); 
                    */
                }

            
                var data = []

                for (var key in raw_data) {
                    data.push({
                        'date': raw_data[key]['date'],
                        'value': raw_data[key]['value']
                    });
                }

            
                //document.body.appendChild(btn);  
            
                var elem = document.getElementById("extension-privacy-manager-thing-dataviz-svg > *");
                if (elem != null) {
                    elem.parentNode.removeChild(elem);
                }
                
                //console.log("svg? ", typeof document.getElementById('extension-privacy-manager-thing-dataviz-svg'));

                //var svg = d3.select("#extension-privacy-manager-thing-dataviz").append("svg"),
                var svg = d3.select("#extension-privacy-manager-thing-dataviz-svg"),
                    margin = {
                        top: 20,
                        right: 40,
                        bottom: 110,
                        left: 40
                    },
                    margin2 = {
                        top: 430,
                        right: 40,
                        bottom: 30,
                        left: 40
                    }
                    //,
                    //width = +svg.attr("width") - margin.left - margin.right,
                    //height = +svg.attr("height") - margin.top - margin.bottom,
                    //height2 = +svg.attr("height") - margin2.top - margin2.bottom;


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
                var width = document.getElementById('extension-privacy-manager-thing-dataviz').offsetWidth - 10;
                //console.log("offsetWidth = " + width);
                document.getElementById('extension-privacy-manager-thing-dataviz-svg').style.width = width + "px";
                //console.log();

                var height = +svg.attr("height")

                width = width - 60;
                height = height - 50;

                //var margin = {top: (0.1*width), right: (0.1*width), bottom: (0.1*width), left: (0.1*width)};
                //var margin = {top: 0, right: (0.1*width), bottom: (0.1*width), left: (0.1*width)};
                var margin = {
                    top: 10,
                    right: 10,
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
                var minimum_time = d3.min(date_array);
                var maximum_time = d3.max(date_array);
                
                // not currently used, but could be useful?
                //var minimum_value = d3.min(value_array); 
                //var maximum_value = d3.max(value_array);

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
                        //console.log("point hover: ", this, d);
                        this.setAttribute('fill-opacity', 1);
                        this.setAttribute('r', 7);
                        
                        const cx = parseInt(this.getAttribute('cx'));
                        const cy = parseInt(this.getAttribute('cy'));
                        
                        if(cx > 40){ // && cy < 350
                            const hoverer = document.getElementById('extension-privacy-manager-sculptor-hoverer');
                            const hoverer_value = document.getElementById('extension-privacy-manager-sculptor-hoverer-value');
                            hoverer_value.innerText = parseFloat(this.getAttribute('data-value')).toFixed(2);
                            hoverer.style.display = 'block';
                        
                            //hoverer.style.left = this.getAttribute('cx' ) + 'px';
                        
                            hoverer.style.width = 50 + cx + 'px';
                            hoverer.style.top = 20 + cy + 'px';
                        }
                        
                        
                        //hoverer.style.height = this.getAttribute('cy' ) + 'px';
                        
                    })
                    .on("mouseout", function(d) {
                        //console.log(this);
                        //console.log("point stop hover: ", this);
                        document.getElementById('extension-privacy-manager-sculptor-hoverer').style.display = 'none';
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
                        //console.log("selected point as date object = " + select);

                        console.log("select date object: ", select, ", month: ", select.getMonth());

                        document.getElementById('extension-privacy-manager-input-change-value').value = this.getAttribute("data-value");
                        document.getElementById('extension-privacy-manager-input-change-property-id').value = this.getAttribute("data-property-id");

                        document.getElementById('extension-privacy-manager-input-second').value = select.getSeconds();
                        document.getElementById('extension-privacy-manager-input-minute').value = select.getMinutes(); //select.toLocaleDateString("en-UK",{minute: '2-digit'});
                        document.getElementById('extension-privacy-manager-input-hour').value = select.getHours();
                        document.getElementById('extension-privacy-manager-input-day').value = select.getDate();
                        //console.log("select.getDate() = ", select.getDate() );
                        //console.log("select.getMonth() = ", select.getMonth() );
                        document.getElementById('extension-privacy-manager-input-month').value = select.getMonth();
                        document.getElementById('extension-privacy-manager-input-year').value = select.getFullYear();
                        document.getElementById('extension-privacy-manager-input-millis').value = select.getMilliseconds();
                        
                        window.scrollTo(0,document.body.scrollHeight);
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
            }
            catch(e){
                console.log("Error showing dataviz: ", e);
            }
            

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





        thing_list_click(the_target) {
            if(this.debug){
                console.log("privacy manager debug: in thing_list_click. the_target: ", the_target);
            }
            
            if(typeof the_target == 'undefined'){
                console.error("thing_list_click: error, missing target");
                return;
            }
            const pre = document.getElementById('extension-privacy-manager-response-data');
            const dataviz_el = document.getElementById('extension-privacy-manager-thing-dataviz');
            
            // Update CSS
            var remove_click_css_list = document.querySelectorAll('#extension-privacy-manager-thing-list > *');
            for (var i = 0, max = remove_click_css_list.length; i < max; i++) {
                this.removeClass(remove_click_css_list[i], "extension-privacy-manager-clicked");
            }
            this.addClass(the_target, "extension-privacy-manager-clicked");

            var target_property_id = the_target.getAttribute('data-property-id');
            var target_data_type = the_target.getAttribute('data-data-type');
            //console.log(target_data_type);
            document.getElementById('extension-privacy-manager-input-change-data-type').value = target_data_type; // Make sure this is always populated with the correct data type. Bit of a clumsy use of hidden fields, should improve later.
            //console.log(target_thing_id);
            
            document.getElementById("extension-privacy-manager-thing-dataviz").scrollIntoView();
            //document.getElementById("extension-privacy-manager-thing-dataviz").innerHTML = '<div style="padding: 15rem 0; text-align:center"><div class="extension-privacy-manager-spinner"><div></div><div></div><div></div><div></div></div></div>';
            document.getElementById("extension-privacy-manager-sculptor-loading-data").style.display = 'flex';
            
            // Get data for selected thing
            dataviz_el.style.opacity = .5;
            window.API.postJson(
                `/extensions/${this.id}/api/get_property_data`, {
                    'property_id': target_property_id,
                    'data_type': target_data_type
                }
            ).then((body) => {
                dataviz_el.style.opacity = 1;
                //console.log(body);
                this.display_thing_data(target_property_id, target_data_type, body['data']);
                
                //pre.innerText = JSON.stringify(body, null, 2);
                //pre.innerText = body['state'];
            }).catch((e) => {
                console.log("Privacy manager: error getting property data: " + e);
                pre.innerText = e.toString();
            });

        }





        //
        // SHOW
        //

        show() {
            if (this.content == '') {
                return;
            } else {
                this.view.innerHTML = this.content;
            }

            const pre = document.getElementById('extension-privacy-manager-response-data');

            // Beauty filters
            const quick_delete_button = document.getElementById('extension-privacy-manager-quick-delete-button');
            
            // Data sculptor
            const thing_list = document.getElementById('extension-privacy-manager-thing-list');
            const dataviz = document.getElementById('extension-privacy-manager-thing-dataviz');

            const tab_button_sculptor = document.getElementById('extension-privacy-manager-tab-button-sculptor');
            const tab_button_internal = document.getElementById('extension-privacy-manager-tab-button-internal-logs');
            const tab_button_things = document.getElementById('extension-privacy-manager-tab-button-things');
            const tab_button_quick = document.getElementById('extension-privacy-manager-tab-button-filters');
            const tab_button_print = document.getElementById('extension-privacy-manager-tab-button-print');
            const tab_button_help = document.getElementById('extension-privacy-manager-tab-button-help');

            const tab_sculptor = document.getElementById('extension-privacy-manager-tab-sculptor');
            const tab_internal = document.getElementById('extension-privacy-manager-tab-internal-logs');
            const tab_quick = document.getElementById('extension-privacy-manager-tab-filters');
            const tab_print = document.getElementById('extension-privacy-manager-tab-print');
            const tab_help = document.getElementById('extension-privacy-manager-tab-help');

            const button_change_point = document.getElementById('extension-privacy-manager-button-change-point');
            const button_create_point = document.getElementById('extension-privacy-manager-button-create-point');
            const button_delete_point = document.getElementById('extension-privacy-manager-button-delete-point');
            const button_delete_before = document.getElementById('extension-privacy-manager-button-delete-before');
            const button_delete_after = document.getElementById('extension-privacy-manager-button-delete-after');
            //const button_delete_and_below = document.getElementById('extension-privacy-manager-button-delete-and-below');
            //const button_delete_and_above = document.getElementById('extension-privacy-manager-button-delete-and-above');
            const button_delete_below = document.getElementById('extension-privacy-manager-button-delete-below');
            const button_delete_above = document.getElementById('extension-privacy-manager-button-delete-above');

            const input_change_value = document.getElementById('extension-privacy-manager-input-change-value');
            const input_change_property_id = document.getElementById('extension-privacy-manager-input-change-property-id');
            const input_change_data_type = document.getElementById('extension-privacy-manager-input-change-data-type');

            // Internal logs
            const internal_logs_auto_delete_checkbox = document.getElementById('extension-privacy-manager-delete-internal-logs-checkbox');
            
            // Print
            const bluetooth_scan_button = document.getElementById('extension-privacy-manager-start-bluetooth-scan-button');

            pre.innerText = "";
            
            API.getThings().then((things) => {
                for (let key in things) {
                    //console.log("lookup device source: ", things[key]);
                    
                    var thing_id = things[key]['href'].substr(things[key]['href'].lastIndexOf('/') + 1);
                    this.thing_title_lookup_table[thing_id] = {'title':things[key]['title'], 'properties':{} };
                    
                    for (let property_name in things[key].properties ) {
                        //console.log("property_name?: ", property_name);
                        //console.log(things[key].properties[property_name]);
                        
                        //things[key].properties[property_name].name
                        //things[key].properties[property_name].title
                        
                        this.thing_title_lookup_table[thing_id].properties[property_name] = things[key].properties[property_name].title;
                        
                    }
                }
                //console.log("complete things lookup table: ", this.thing_title_lookup_table);
            });

            
            // TABS
            document.getElementById('extension-privacy-manager-tab-buttons-container').addEventListener('click', (event) => {
                var active_tab = event.target.innerText.toLowerCase().replace(/\s/g , "-");
                if(event.target.classList[0] == "extension-privacy-manager-main-tab-button"){
                    if(active_tab == "?"){active_tab = "help";}
                    if(this.debug){
                        console.log("privacy manager debug: clicked on privay manager menu tab button: ", active_tab);
                    }
                    document.getElementById('extension-privacy-manager-content').className = 'extension-privacy-manager-active-tab-' + active_tab;
                }
            });
            

            // Print
            tab_button_things.addEventListener('click', (target) => {
                //this.scan_for_printer();
                this.generate_things_overview();
            });

            
            // Print
            tab_button_print.addEventListener('click', (target) => {
                //console.log("showing print tab and calling printer_init");
                //this.scan_for_printer();
                this.show_printer_state();
            });
            
            // Data sculptor tab
            tab_button_sculptor.addEventListener('click', () => {                
                this.init_data_sculptor();
            });
            
            
            // Internal logs tab
            tab_button_internal.addEventListener('click', () => {

                window.API.postJson(
                    `/extensions/${this.id}/api/internal_logs`, {
                        'action': 'get',
                        'filename': 'all'
                    }

                ).then((body) => {
                    //console.log(body);
                    //thing_list.innerText = body['data'];
                    this.show_internal_logs(body['data']);

                }).catch((e) => {
                    //pre.innerText = e.toString();
                    console.log("Privacy manager: error in tab-button0internal click api call:", e);
                });

            });
            
            
            // BEAUTY FILTERS
            
            // Quick delete button
            quick_delete_button.addEventListener('click', () => {
                const duration = document.getElementById("extension-privacy-manager-quick-delete-time-dropdown").value;
                //console.log("quick delete button pressed. duration: " + duration);
                

                window.API.postJson(
                    `/extensions/${this.id}/api/ajax`, {
                        'action': 'quick_delete',
                        'duration': duration
                    }

                ).then((body) => {
                    //console.log("quick delete ajax API was called succcesfully: ", body);
                    //thing_list.innerText = body['data'];
                    //this.show_internal_logs(body['data']);

                }).catch((e) => {
                    //pre.innerText = e.toString();
                    console.log("Privacy manager: error in quick delete response: ", e);
                });

            });
            
            
            
            // PRINT BUTTONS
            
            bluetooth_scan_button.addEventListener('click', (target) => {
                //console.log("Bluetooth printer scan button clicked");
                this.scan_for_printer();
            });
            
            document.getElementById('extension-privacy-manager-set-print-button').addEventListener('click', (target) => {
                //console.log("set print button clicked");
                this.set_print();
            });
            
            
            // printer test button
            document.getElementById('extension-privacy-manager-print-test-button').addEventListener('click', (target) => {
                //console.log("printer test button clicked");
                
                document.getElementById('extension-privacy-manager-printer-connected').innerText = '?';
                
                document.getElementById('extension-privacy-manager-print-test-button').style.display = 'none';
                document.getElementById('extension-privacy-manager-print-test-progress').style.display = 'block';
                window.API.postJson(
                    `/extensions/${this.id}/api/print_test` //,{'printer_log':printer_log, 'printer_interval':printer_interval}

                ).then((body) => {
                    //console.log(body);
                    if(body.printer_connected == false){
                        alert("Could not connect to printer. Try turning it on and off again.");
                    }
                    else if(this.debug){
                        console.log("Printer connection test was succesful");
                        //alert("Printer is connected");
                    }
                    
                    if(typeof body.printer_connected != 'undefined'){
                        this.show_printer_connection_state(body.printer_connected);
                    }
                    
                    document.getElementById('extension-privacy-manager-print-test-progress').style.display = 'none';
                    document.getElementById('extension-privacy-manager-print-test-button').style.display = 'block';
                }).catch((e) => {
                    console.log("Privacy manager: error in print test: ", e);
                    //alert('Error: could not connect to the controller');
                    document.getElementById('extension-privacy-manager-print-test-progress').style.display = 'none';
                    document.getElementById('extension-privacy-manager-print-test-button').style.display = 'block';
                    this.show_printer_connection_state(false);
                });
            });
            
            
            // Forget printer button
            document.getElementById('extension-privacy-manager-forget-printer-button').addEventListener('click', (target) => {
                //console.log("printer forget button clicked");
                document.getElementById('extension-privacy-manager-forget-printer-button').style.display = 'none';
                
                
                window.API.postJson(
                    `/extensions/${this.id}/api/forget_printer` //,{'printer_log':printer_log, 'printer_interval':printer_interval}
                ).then((body) => {
                    if(this.debug){
                        console.log("Privacy manager: forget printer response: ", body);
                    }
                    
                    document.getElementById('extension-privacy-manager-print-test-button').style.display = 'none';
                    document.getElementById('extension-privacy-manager-printer-connected').innerText = "";
                    document.getElementById('extension-privacy-manager-printer-list-name').innerText = "";
                    document.getElementById('extension-privacy-manager-printer-list-mac').innerText = "";
                }).catch((e) => {
                    console.log("Privacy manager: error in forget printer response: ", e);
                    document.getElementById('extension-privacy-manager-forget-printer-button').style.display = 'block';
                });
            });
            
            
            
            // print now button
            document.getElementById('extension-privacy-manager-print-now-button').addEventListener('click', (target) => {
                //console.log("print now button clicked");
                if(confirm("Are you sure? This will print and then delete all existing data for this particular log.")){
                    window.API.postJson(
                        `/extensions/${this.id}/api/print_now` //,{'printer_log':printer_log, 'printer_interval':printer_interval}

                    ).then((body) => {
                        //console.log(body);
                        
                        if(body.print_result.state == 'error'){
                            if(typeof body.print_result.message != 'undefined'){
                                alert("Error: " + body.print_result.message);
                            }
                            else{
                                alert("Could not print. Perhaps the printer is not connected, or there is no data to print?")
                            }
                            
                        }
                        else{
                            //console.log("test print was succesful");
                        }
                        
                    }).catch((e) => {
                        console.log("Privacy manager: error in print now: ", e);
                    });
                }
                
            });
            
            
            
            // Print icon
            document.getElementById('extension-privacy-manager-printable-icons-list').addEventListener('click', (event) => {
                //console.log("print icon button clicked");
                if(confirm("Are you sure you want to print this icon?")){
                    
                    const filename = event.target.getAttribute('data-filename');
                    //console.log("filename: ", filename);
                    
                    window.API.postJson(
                        `/extensions/${this.id}/api/print_image`, //,{'printer_log':printer_log, 'printer_interval':printer_interval}
                            {'filename':filename}
                    ).then((body) => {
                        //console.log(body);
                        
                        if(body.state == 'error'){
                            alert("Error, could not print the file")
                        }
                        else{
                            //console.log("image was sent to printer");
                        }
                        
                    }).catch((e) => {
                        console.log("Privacy manager: error in print icon: ", e);
                        alert('Could not print icon - connection error');
                    });
                }
                
            });
            
            
            
            
            
            
            //
            //  DATA SCULPTOR BUTTONS
            //
            


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



            /*
            // DELETE AND ALL BELOW
            button_delete_and_below.addEventListener('click', () => {
                //console.log("clicked delete after");
                this.delete_handler("delete-and-below");
            });
            
            // DELETE AND ALL ABOVE
            button_delete_and_above.addEventListener('click', () => {
                //console.log("clicked delete after");
                this.delete_handler("delete-and-above");
            });
            */
            
            // DELETE BELOW
            button_delete_below.addEventListener('click', () => {
                //console.log("clicked delete after");
                this.delete_handler("delete-below");
            });
            
            // DELETE ABOVE
            button_delete_above.addEventListener('click', () => {
                //console.log("clicked delete after");
                this.delete_handler("delete-above");
            });
            


            // Get initial data
            
            window.API.postJson(
                `/extensions/${this.id}/api/init` //,{'init':1}

            ).then((body) => {
                if(this.debug){
                    console.log("Privacy manager debug: init data: ", body);
                }
                
                //thing_list.innerText = body['data'];
                //this.create_sculptor_thing_list(body['logs']);
                
                
                
                
                if(typeof body.debug != 'undefined'){
                    this.debug = body.debug;
                    if(body.debug){
                        if(document.getElementById('extension-privacy-manager-debug-warning') != null){
                            document.getElementById('extension-privacy-manager-debug-warning').style.display = 'block';
                        }
                        console.log("privacy manager init response: ", body);
                    }
                }
                
                 if(typeof body.persistent != 'undefined'){
                     this.persistent = body['persistent'];
                     
                     if(typeof body['persistent']['duration'] != 'undefined'){
                         //console.log("setting dropdown to duration: ", body['persistent']['duration']);
                         if(document.getElementById('extension-privacy-manager-quick-delete-time-dropdown') != null){
                             document.getElementById('extension-privacy-manager-quick-delete-time-dropdown').value = body['persistent']['duration'];
                         }
                         
                     }
                     
                 }
                
                if(typeof body.internal_logs_auto_delete != 'undefined'){
                    //console.log("setting auto-delete internal logs preference to: " + body.internal_logs_auto_delete);
                    //console.log(internal_logs_auto_delete_checkbox.checked);
                    internal_logs_auto_delete_checkbox.checked = Boolean(body.internal_logs_auto_delete);
                    
                    internal_logs_auto_delete_checkbox.addEventListener('change', (event) => {
                        //console.log("changed delete internal logs checkbox state");
                        this.internal_logs_auto_delete(event.target.checked);
                    });
                }
                

            }).catch((e) => {
                console.log("Privacy manager: error in show call to api/init: ", e);
            });
            

            // Generate initial things overview
            this.generate_things_overview();



            // DELETE ALL INTERNAL LOGS BUTTON
            document.getElementById('extension-privacy-manager-button-delete-all-logs').addEventListener('click', () => {
                //console.log("clicked delete all internal logs");
                this.delete_internal_logs("all");
            });
            
            

        }



		hide(){
			//console.log("in hide");
			//clearInterval(window.zigbee2mqtt_interval);
			//this.view.innerHTML = "";
            
			try{
                if(document.getElementById('extension-privacy-manager-menu-item').classList.contains('selected') == false){
                    this.view.innerHTML = "";
                }
			}
            catch(e){
                console.log("Privacy manager addon: error in hide(): ", e);
            }
            
		}





        //
        //  DATA SCULPTOR
        //


        init_data_sculptor(){
            //console.log("in init_data_sculptor");
            window.API.postJson(
                `/extensions/${this.id}/api/sculptor_init` //,{'init':1}

            ).then((body) => {
                if(this.debug){
                    console.log("Data sculptor init response: ", body);
                }
                //thing_list.innerText = body['data'];
                this.create_sculptor_thing_list(body['logs']);

            }).catch((e) => {
                //pre.innerText = e.toString();
                //console.log("Privacy manager: error in show function");
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
            if(this.debug){
                console.log("Deleting point(s). Action:", action);
            }
            /*
			console.log("Deleting point(s). Action:");
			console.log(action);
            //console.log(input_change_date.value);
			
			console.log("min-time: " + this.min_time);
			console.log("min-time: " + this.max_time);
			*/
            //const pre = document.getElementById('extension-privacy-manager-response-data');
            const options_pane = document.getElementById('extension-privacy-manager-thing-options');
            //const input_change_value = document.getElementById('extension-privacy-manager-input-change-value');

            var updating_data_type = document.getElementById('extension-privacy-manager-input-change-data-type').value;
            var updating_property_id = document.getElementById('extension-privacy-manager-input-change-property-id').value;

            const value = document.getElementById('extension-privacy-manager-input-change-value').value;

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
            
            if(this.debug){
    			console.log("____action = " + action);
                console.log("property = " + updating_property_id);
    			console.log("of type = " + updating_data_type);
                console.log("end_date_stamp = " + end_date_stamp);
                console.log("start_date_stamp = " + start_date_stamp);
                console.log("value = " + value);
            }
            options_pane.style.opacity = .5;


            window.API.postJson(
                `/extensions/${this.id}/api/point_delete`, {
                    'action': action,
                    'property_id': updating_property_id,
                    'data_type': updating_data_type,
                    'start_date': start_date_stamp,
                    'end_date': end_date_stamp,
                    'value': value
                }
            ).then((body) => {
                options_pane.style.opacity = 1;
                if(this.debug){
                    console.log("Delete response: ", body['data']);
                }

                document.getElementById('extension-privacy-manager-input-change-old-epoch').value = "";
                document.getElementById('extension-privacy-manager-input-change-value').value = "";

                // Update the dataviz
                this.display_thing_data(updating_property_id, updating_data_type, body['data']);

            }).catch((e) => {
                console.log("Privacy manager: error in deletion handler: ", e);
                options_pane.style.opacity = 1;
                document.getElementById('extension-privacy-manager-sculptor-delete-failed-message').style.display = 'block';
                //pre.innerText = e.toString();
                setTimeout(function(){
                    document.getElementById('extension-privacy-manager-sculptor-delete-failed-message').style.display = 'none';
                }, 4000);
            });

        } // End of button delete point add listener




        //
        //  INTERNAL LOGS
        //


        show_internal_logs(file_list) {
            if(this.debug){
                console.log("privacy manager debug: in show_internal_logs. File list: ", file_list);
            }
            try{
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
            catch(e){
                console.log("Error in show_internal_logs: ", e);
            }
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
                console.log("Privacy manager: error in internal log deletion handler: ", e);
                pre.innerText = e.toString();
            });

        } // End of button delete point add listener



        internal_logs_auto_delete(choice) {
            //console.log("Deleting log files. filename:");
            //console.log(filename);

            //const choice = document.getElementById('extension-privacy-manager-delete-internal-logs-checkbox').checked;
            //console.log("choice:" + choice);

            window.API.postJson(
                `/extensions/${this.id}/api/internal_logs`, {
                    'action': 'auto-delete',
                    'internal_logs_auto_delete': choice
                }

            ).then((body) => {
                //console.log("choice set: ", body);
                //this.show_internal_logs(body['data']);

            }).catch((e) => {
                console.log("Privacy manager: error in internal log automatic deletion change handler");
            });

        } // End of button delete point add listener




        //
        //  BLUETOOTH PRINTER
        //

        scan_for_printer(){
            if(this.debug){
                console.log("scan_for_printer was called. Calling API for /printer_scan");
            }
            document.getElementById('extension-privacy-manager-print-busy-scanning').style.display = 'block';
            document.getElementById('extension-privacy-manager-start-bluetooth-scan-button').style.display = 'none';
            
            window.API.postJson(
                `/extensions/${this.id}/api/printer_scan` //,{'init':1}

            ).then((body) => {
                console.log(body);
                if(body['persistent']['printer_mac'] != ""){
                    console.log("printer mac: ", body['persistent']['printer_mac']);
                    document.getElementById('extension-privacy-manager-printer-list-name').innerText = body['persistent']['printer_name'];
                    document.getElementById('extension-privacy-manager-printer-list-mac').innerText = body['persistent']['printer_mac'];
                    document.getElementById('extension-privacy-manager-print-test-button').style.display = 'block';
                    document.getElementById('extension-privacy-manager-forget-printer-button').style.display = 'block';
                    
                }
                
                
                //thing_list.innerText = body['data'];
                //this.create_sculptor_thing_list(body['logs']);
                //this.create_printer_ui(body, true);
                document.getElementById('extension-privacy-manager-print-busy-scanning').style.display = 'none';
                document.getElementById('extension-privacy-manager-start-bluetooth-scan-button').style.display = 'block';
                

            }).catch((e) => {
                //pre.innerText = e.toString();
                console.log("Privacy manager: error in show function: ", e);
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
        show_printer_connection_state(connected){
            if(connected){
                document.getElementById('extension-privacy-manager-printer-connected').innerHTML = "⇄";
                document.getElementById('extension-privacy-manager-printer-connected').style.background = "green";
                document.getElementById('extension-privacy-manager-view').classList.add('extension-privacy-manager-printer-connected');
            }
            else{
                document.getElementById('extension-privacy-manager-printer-connected').innerHTML = "?";
                document.getElementById('extension-privacy-manager-printer-connected').style.background = "red";
                document.getElementById('extension-privacy-manager-view').classList.remove('extension-privacy-manager-printer-connected');
            }
        }

        show_printer_state(scanning){
            if(typeof scanning != 'undefined'){
                // show still scanning
            }
            
            window.API.postJson(
                `/extensions/${this.id}/api/printer_init` //,{'init':1}

            ).then((body) => {
                //console.log(body);
                if(body.scanning){
                    document.getElementById('extension-privacy-manager-start-bluetooth-scan-button').style.display = 'none';
                }
                else{
                    console.log("not currently scanning for a printer");
                    document.getElementById('extension-privacy-manager-start-bluetooth-scan-button').style.display = 'block';
                }

                
                // if still scanning is true, also call wait_for_printer_state again (and make sure the "still scanning" message is shown)
                // if scanning is done, just remove the "still scanning" message
                document.getElementById('extension-privacy-manager-printer-list-name').innerText = body['persistent']['printer_name'];
                document.getElementById('extension-privacy-manager-printer-list-mac').innerText = body['persistent']['printer_mac'];
                
                if(body['persistent']['printer_mac'] != ""){
                    document.getElementById('extension-privacy-manager-print-test-button').style.display = 'block';
                    document.getElementById('extension-privacy-manager-forget-printer-button').style.display = 'block';
                    if(typeof body.printer_connected != 'undefined'){
                        this.show_printer_connection_state(body.printer_connected);
                    }
                }
                
                // Clean slate - print everything
                if( typeof body['persistent']['printer_log_name'] != 'undefined'){
                    if(body['persistent']['printer_log_name'] != "None"){
                        document.getElementById('extension-privacy-manager-selected-log-to-print').innerText = body['persistent']['printer_log_name'];
                        //document.getElementById('extension-privacy-manager-clean-slate-container').style.display = 'block';
                    }
                }
                
                
                
                // Interval select correct option
                if(typeof body['persistent']['printer_interval'] != 'undefined'){
                    //console.log("body['printer_interval'] = " + body['persistent']['printer_interval']);
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
                    //console.log("body['printer_rotation'] = " + body['persistent']['printer_rotation']);
                    var rotation_dropdown = document.getElementById('extension-privacy-manager-printer-rotation-dropdown');
                    for (var i = 0; i < rotation_dropdown.options.length; i++) {
                        //console.log(rotation_dropdown.options[i].value + " =?= " + body['persistent']['printer_rotation']);
                        if( parseInt(rotation_dropdown.options[i].value) === parseInt(body['persistent']['printer_rotation']) ){
                            //console.log("correct rotation spotted");
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
                    //console.log("logs list: ", logs_list[key]);
                    var dataline = JSON.parse(logs_list[key]['name']);
                    //console.log(Object.keys(dataline));

                    //var this_object = this;
                    //console.log(this_object);

                    //var node = document.createElement("LI"); // Create a <li> node
                    //node.setAttribute("data-property-id", logs_list[key]['id']);
                    //node.setAttribute("data-data-type", logs_list[key]['data_type']);
                    //var human_readable_thing_title = dataline['thing'];
                    //var human_readable_property_title = dataline['property'];
                    const nice_title = this.get_thing_and_property_string(dataline['thing'], dataline['property']);
                    
                    
                    var new_option = new Option(nice_title,logs_list[key]['id']);
                    if(typeof body['persistent']['printer_log'] != 'undefined'){
                        if( body['persistent']['printer_log'] == logs_list[key]['id'] ){
                            //console.log("setting selected log: " + logs_list[key]['id']);
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
                //console.log( document.getElementById('extension-privacy-manager-printer-log-dropdown-container') );
                document.getElementById('extension-privacy-manager-printer-log-dropdown-container').innerHTML = "";
                document.getElementById('extension-privacy-manager-printer-log-dropdown-container').append(log_to_print_dropdown);
                
                

            }).catch((e) => {
                //pre.innerText = e.toString();
                console.log("Privacy manager: error in show_printer_state function", e);
            });
        }



        get_thing_and_property_string(human_readable_thing_title, human_readable_property_title){
            
            if (human_readable_thing_title in this.thing_title_lookup_table) {
                
                // try to upgrade the property title
                try{
                    human_readable_property_title = this.thing_title_lookup_table[human_readable_thing_title].properties[ human_readable_property_title ];
                }
                catch(e){
                    console.log("error looking up nice property name: ", e);
                }
                
                // Upgrade thing title and append property title
                human_readable_thing_title = this.thing_title_lookup_table[human_readable_thing_title].title + ' - ' + human_readable_property_title;
            }
            //console.log("original title after lookup: ", human_readable_thing_title);
            return human_readable_thing_title;
            //console.log(human_readable_thing_title);
        }


        // Save print settings
        set_print(){
            //console.log('in set_print');
            
            const selected_log_element = document.getElementById("extension-privacy-manager-log-to-print");
            var printer_log = selected_log_element.options[selected_log_element.selectedIndex].value;
            var printer_log_name = selected_log_element.options[selected_log_element.selectedIndex].text;
            
            const selected_log_interval_element = document.getElementById("extension-privacy-manager-printer-interval-dropdown");
            var printer_interval = selected_log_interval_element.options[selected_log_interval_element.selectedIndex].value;
            
            const selected_rotation_element = document.getElementById("extension-privacy-manager-printer-rotation-dropdown");
            var printer_rotation = selected_rotation_element.options[selected_rotation_element.selectedIndex].value;
            
            document.getElementById('extension-privacy-manager-print-settings-saved').style.display = 'block';
            
            window.API.postJson(
                `/extensions/${this.id}/api/printer_set`,{'printer_log':printer_log, 'printer_interval':printer_interval, 'printer_log_name':printer_log_name, 'printer_rotation':printer_rotation}

            ).then((body) => {
                //console.log(body);
                
                document.getElementById('extension-privacy-manager-printer-list-name').innerText = body['persistent']['printer_name'];
                document.getElementById('extension-privacy-manager-printer-list-mac').innerText = body['persistent']['printer_mac'];
                
                //thing_list.innerText = body['data'];
                //this.create_sculptor_thing_list(body['logs']);
                //this.create_printer_ui(body, true);
                //document.getElementById('extension-privacy-manager-print-busy-scanning').style.display = 'none';
                //document.getElementById('extension-privacy-manager-start-bluetooth-scan-button').style.display = 'block';
                
                document.getElementById('extension-privacy-manager-print-settings-saved').style.display = 'block';
                setTimeout(() => {
                    document.getElementById('extension-privacy-manager-print-settings-saved').style.display = 'none';
                }, 2000);

            }).catch((e) => {
                //pre.innerText = e.toString();
                console.log("Privacy manager: error while saving print settings: ", e);
                //document.getElementById('extension-privacy-manager-print-busy-scanning').style.display = 'none';
                //document.getElementById('extension-privacy-manager-start-bluetooth-scan-button').style.display = 'block';
                
                document.getElementById('extension-privacy-manager-print-settings-saved-error').style.display = 'block';
                setTimeout(() => {
                    document.getElementById('extension-privacy-manager-print-settings-saved-error').style.display = 'none';
                }, 3000);
            });
            
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


    }
    new PrivacyManager();

})();