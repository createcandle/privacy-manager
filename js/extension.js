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
				for (let key in things){
					var thing_id = things[key]['href'].substr(things[key]['href'].lastIndexOf('/') + 1);
					this.thing_title_lookup_table[thing_id] = things[key]['title'];
				}
	    });			
			
			var latest_property_id = 4;

      fetch(`/extensions/${this.id}/views/content.html`)
        .then((res) => res.text())
        .then((text) => {
          this.content = text;
        })
        .catch((e) => console.error('Failed to fetch content:', e));
    }

		create_thing_list(body){
			//console.log("Creating main thing list");
			
			const pre = document.getElementById('extension-privacy-manager-response-data');
			const thing_list = document.getElementById('extension-privacy-manager-thing-list');

			for (var key in body['data']) {

				var dataline = JSON.parse(body['data'][key]['name']);
				//console.log(Object.keys(dataline));
				
				var this_object = this;
				//console.log(this_object);
				
				var node = document.createElement("LI");                 // Create a <li> node
				node.setAttribute("data-property-id", body['data'][key]['id']); 
				node.setAttribute("data-data-type", body['data'][key]['data_type']); 
				var human_readable_thing_title = dataline['thing'];
				if( human_readable_thing_title in this.thing_title_lookup_table ){
					human_readable_thing_title = this.thing_title_lookup_table[human_readable_thing_title];
				}
				var textnode = document.createTextNode(human_readable_thing_title + ' - ' + dataline['property']);         // Create a text node
				node.onclick = function() { this_object.thing_list_click(this) };
				node.appendChild(textnode); 
				thing_list.appendChild(node);
			}
			pre.innerText = "";
		}
		
		
		
		display_thing_data(property_id,data_type,raw_data){ // Uses json to generate dataviz
			const dataviz = document.getElementById('extension-privacy-manager-thing-dataviz');
			var data = []
			
			for( var key in raw_data ){
				data.push({'date': raw_data[key]['date'], 'value': raw_data[key]['value']});
			}
			
			var elem = document.getElementById("extension-privacy-manager-thing-dataviz-svg > *");
			if( elem != null ){
				elem.parentNode.removeChild(elem);
			}
			

            //var svg = d3.select("#extension-privacy-manager-thing-dataviz").append("svg"),
            var svg = d3.select("#extension-privacy-manager-thing-dataviz-svg"),
                margin = {top: 20, right: 20, bottom: 110, left: 40},
                margin2 = {top: 430, right: 20, bottom: 30, left: 40},
                width = +svg.attr("width") - margin.left - margin.right,
                height = +svg.attr("height") - margin.top - margin.bottom,
                height2 = +svg.attr("height") - margin2.top - margin2.bottom;


            svg.selectAll("*").remove();            

            var date_array = [];
            var value_array = [];

            data.forEach(function (arrayItem) {
                date_array.push(  new Date(arrayItem['date']) );
                value_array.push( arrayItem['value'] );
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
						var margin = {top: 10, right: 0, bottom: 0, left: 50};

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
						
						if(minimum_time < this.min_time){
							this.min_time = minimum_time;
						}
						if(maximum_time > this.max_time){
							this.max_time = maximum_time;
						}
						
            // create scale objects
            var xScale = d3.scaleTime()
              //.domain(d3.extent(date_array))
							.domain([minimum_time,maximum_time])
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
                  .attr('cx', function(d) {return xScale(new Date(d.date))})
                  .attr('cy', function(d) {return yScale(d.value)})
                  .attr('r', 5)
                  .style("fill-opacity", .5)
                  .attr('class', 'extension-privacy-manager-svg-circle')
                  .attr("data-value", function(d) { return d.value; })
                  .attr("data-date", function(d) { return d.date; })
                  .attr("data-property-id", property_id )
									.attr("data-data-type", data_type );

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
              .extent([[0, 0], [width, height]])
              .on("zoom", zoomed);

            rectangle_overlay.call(zoom);
						
            function zoomed() {
                
								// Create new scale
                var new_xScale = d3.event.transform.rescaleX(xScale);
                var new_yScale = d3.event.transform.rescaleY(yScale);
								
                // Update axis
                gX.call(xAxis.scale(new_xScale));
                
								points.data(data)
                 .attr('cx', function(d) {return new_xScale(d.date)})
                 .attr('cy', function(d) {return yScale(d.value)})
            }
            
		}
		
		
		
		
		// HELPER METHODS
		
		hasClass(ele,cls) {
			//console.log(ele);
			//console.log(cls);
		  return !!ele.className.match(new RegExp('(\\s|^)'+cls+'(\\s|$)'));
		}

		addClass(ele,cls) {
		  if (!this.hasClass(ele,cls)) ele.className += " "+cls;
		}

		removeClass(ele,cls) {
		  if (this.hasClass(ele,cls)) {
		    var reg = new RegExp('(\\s|^)'+cls+'(\\s|$)');
		    ele.className=ele.className.replace(reg,' ');
		  }
		}
		
		
		thing_list_click(the_target){
			const pre = document.getElementById('extension-privacy-manager-response-data');
			
			// Update CSS
			var remove_click_css_list = document.querySelectorAll('#extension-privacy-manager-thing-list > *');
			for (var i=0, max=remove_click_css_list.length; i < max; i++) {
				this.removeClass(remove_click_css_list[i],"clicked");
			}
			this.addClass(the_target,"clicked");
			
			var target_property_id = the_target.getAttribute('data-property-id');
			var target_data_type = the_target.getAttribute('data-data-type');
			//console.log(target_data_type);
			document.getElementById('extension-privacy-manager-input-change-data-type').value = target_data_type; // Make sure this is always populated with the correct data type. Bit of a clumsy use of hidden fields, should improve later.
			//console.log(target_thing_id);
			
			// Get data for selected thing
      window.API.postJson(
        `/extensions/${this.id}/api/get_property_data`,
        {'property_id': target_property_id, 'data_type':target_data_type}
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
      this.view.innerHTML = this.content;

			const pre = document.getElementById('extension-privacy-manager-response-data');
	  	const thing_list = document.getElementById('extension-privacy-manager-thing-list');
			const dataviz = document.getElementById('extension-privacy-manager-thing-dataviz');
		
			const tab_button_sculptor = document.getElementById('extension-privacy-manager-tab-button-sculptor');
			const tab_button_internal = document.getElementById('extension-privacy-manager-tab-button-internal');

			const tab_sculptor = document.getElementById('extension-privacy-manager-tab-sculptor');
			const tab_internal = document.getElementById('extension-privacy-manager-tab-internal');

			const button_change_point = document.getElementById('extension-privacy-manager-button-change-point');
			const button_create_point = document.getElementById('extension-privacy-manager-button-create-point');
      const button_delete_point = document.getElementById('extension-privacy-manager-button-delete-point');
			const button_delete_before = document.getElementById('extension-privacy-manager-button-delete-before');
			const button_delete_after = document.getElementById('extension-privacy-manager-button-delete-after');
                  
			const input_change_value = document.getElementById('extension-privacy-manager-input-change-value');
			const input_change_property_id = document.getElementById('extension-privacy-manager-input-change-property-id');
			const input_change_data_type = document.getElementById('extension-privacy-manager-input-change-data-type');

			pre.innerText = "";



			// TABS

			// Data sculptor
      tab_button_sculptor.addEventListener('click', () => {
				this.addClass(tab_button_sculptor,"extension-privacy-manager-button-active");
				this.removeClass(tab_button_internal,"extension-privacy-manager-button-active");
				
				this.addClass(tab_internal,"extension-privacy-manager-hidden");
				this.removeClass(tab_sculptor,"extension-privacy-manager-hidden");
      });

			// Internal logs tab
      tab_button_internal.addEventListener('click', () => {
				this.addClass(tab_button_internal,"extension-privacy-manager-button-active");
				this.removeClass(tab_button_sculptor,"extension-privacy-manager-button-active");
				
				this.addClass(tab_sculptor,"extension-privacy-manager-hidden");
				this.removeClass(tab_internal,"extension-privacy-manager-hidden");
				
	      window.API.postJson(
	        `/extensions/${this.id}/api/internal_logs`,
					{'action':'get' ,'filename':'all'}
        
	      ).then((body) => {
	      	//thing_list.innerText = body['data'];
	        this.show_internal_logs(body['data']);

	      }).catch((e) => {
	        //pre.innerText = e.toString();
					console.log("Privacy manager: error in show function");
					console.log(e.toString());
	      });
				
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
			
      window.API.postJson(
        `/extensions/${this.id}/api/init` //,{'init':1}
        
      ).then((body) => {
      	//thing_list.innerText = body['data'];
        this.create_thing_list(body);

      }).catch((e) => {
        //pre.innerText = e.toString();
				console.log("Privacy manager: error in show function");
				console.log(e.toString());
      });
			
			
			
			//
			// INITIALISE INTERNAL LOGS BUTTONS
			//
			
			// DELETE ALL INTERNAL LOGS
			document.getElementById('extension-privacy-manager-button-delete-all-logs').addEventListener('click', () => {
				//console.log("clicked delete all internal logs");
				this.delete_internal_logs("all");
			});
			
			
    }
		
		
    get_new_date(){
        var fresh_date = new Date(0);
        //console.log(fresh_date);
        fresh_date.setFullYear( document.getElementById('extension-privacy-manager-input-year').value );
        fresh_date.setMonth( document.getElementById('extension-privacy-manager-input-month').value );
        fresh_date.setDate( document.getElementById('extension-privacy-manager-input-day').value );
        fresh_date.setHours( document.getElementById('extension-privacy-manager-input-hour').value );
        fresh_date.setMinutes( document.getElementById('extension-privacy-manager-input-minute').value );
        fresh_date.setSeconds( document.getElementById('extension-privacy-manager-input-second').value );
        fresh_date.setMilliseconds( document.getElementById('extension-privacy-manager-input-millis').value );
        
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
		
		
		change_handler(action){
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
			
			if( action == "create" && old_date_stamp == new_date_stamp ){
				//console.log("Shouldn't make a new point at the same date as the old one.")
				pre.innerText = "Please change the date of the new point.";
				return
			}
			
		  window.API.postJson(
		    `/extensions/${this.id}/api/point_change_value`,
		    {'action':action, 'property_id':updating_property_id, 'data_type': updating_data_type ,'new_value':input_change_value, 'old_date': old_date_stamp, 'new_date': new_date_stamp,}
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
		
		
		
		delete_handler(action){
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
			if( action == "delete-point" ){
				var start_date_stamp = selected_point_date
      	var end_date_stamp   = selected_point_date; //this.get_new_date(); // reconnect all the pieces from the dropdowns (and the hidden milliseconds value) into the new date
			}
			else if( action == "delete-before" ){
				var start_date_stamp = this.min_time.getTime(); //toUTCString();
				var end_date_stamp = selected_point_date;
			}
			else if( action == "delete-after" ){
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
        `/extensions/${this.id}/api/point_delete`,
        {'action':action, 'property_id':updating_property_id, 'data_type':updating_data_type, 'start_date':start_date_stamp, 'end_date':end_date_stamp}
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
				
				var node = document.createElement("LI");                 					// Create a <li> node
				node.setAttribute("class", "extension-privacy-manager-deletable_item" ); 
				node.setAttribute("data-filename", file_list[key] );
				
				var textnode = document.createTextNode( file_list[key] );         // Create a text node
				node.onclick = function() { 
					this_object.delete_internal_logs( file_list[key] ) 
				};
				node.appendChild(textnode); 
				
				logs_list.appendChild(node);
			}
			pre.innerText = "";
		}

		
		
		delete_internal_logs(filename){
      //console.log("Deleting log files. filename:");
			//console.log(filename);
			
			const pre = document.getElementById('extension-privacy-manager-response-data');
			const logs_list = document.getElementById('extension-privacy-manager-logs-list');
		
      window.API.postJson(
        `/extensions/${this.id}/api/internal_logs`,
        {'action':'delete', 'filename':filename}
				
      ).then((body) => { 
				//console.log(body);
        this.show_internal_logs(body['data']);

      }).catch((e) => {
				console.log("Privacy manager: error in internal log deletion handler");
        pre.innerText = e.toString();
      });
    
    } // End of button delete point add listener
		
  }

  new PrivacyManager();
	
})();


