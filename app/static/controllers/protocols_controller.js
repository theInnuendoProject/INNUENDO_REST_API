/**
 * Controller of the protocols page. Interacts with the protocols.js file to
 * create new protocols
 */
innuendoApp.controller("protocolsCtrl", ($scope, $http) => {

    $scope.required = true;

    const backButtonEl = $("#backbutton");

    current_scope_template = $scope.selectedTemplate.path;

    if(PREVIOUS_PAGE_ARRAY.length > 0) backButtonEl.css({"display":"block"});
    else backButtonEl.css({"display":"none"});

    $("#innuendofooter").css({"display":"none"});

    backButtonEl.off("click").on("click", () => {
        $scope.$apply(() => {
            session_array = PREVIOUS_PAGE_ARRAY.pop();

            CURRENT_PROJECT_ID = session_array[1];
            CURRENT_JOB_MINE = session_array[2];
            CURRENT_PROJECT = session_array[3];
            CURRENT_SPECIES_ID = session_array[4];
            CURRENT_SPECIES_NAME = session_array[5];
            CURRENT_USER_NAME = session_array[6];
            CURRENT_JOBS_ROOT = session_array[7];

            CURRENT_JOB_ID = session_array[8];
            CURRENT_PROJECT_NAME_ID = session_array[9];
            CURRENT_TABLE_ROWS_SELECTED = session_array[10];
            CURRENT_TABLE_ROW_ANALYSIS_SELECTED = session_array[11];
            PROJECT_STATUS = session_array[12];

            $scope.selectedTemplate.path = session_array[0];
        })
    });

    $('#waiting_spinner').css({display:'block', position:'fixed', top:'40%', left:'50%'});

    $("#projects_button_li").css({"display":"none"});
    $("#reports_button_li").css({"display":"none"});
    $("#uploads_button_li").css({"display":"none"});
    $("#tools_button_li").css({"display":"none"});
    $("#user_tools").css({"display":"none"});
    $("#workflows_button_li").css({"display":"block"});
    $("#protocols_button_li").css({"display":"block"});
    $("#species_drop_button_li").css({"display":"none"});
    $("#overview_li").css({"display":"block"});


    $("#new_protocol_tab").on("click", () => {
        $("#new_protocol_tab").addClass("active");
        $("#available_protocols_tab").removeClass("active");
        $("#div_available_protocols").css({"display":"none"});
        $("#div_new_protocol").css({"display":"block"});
    });

    $("#available_protocols_tab").on("click", () => {
        $("#available_protocols_tab").addClass("active");
        $("#new_protocol_tab").removeClass("active");
        $("#div_available_protocols").css({"display":"block"});
        $("#div_new_protocol").css({"display":"none"});
    });

    for (const interval in intervals_running){
        if(intervals_running.hasOwnProperty(interval)){
            clearInterval(intervals_running[interval]);
        }
    }

    //RESET ROW SELECTION
    CURRENT_TABLE_ROW_ANALYSIS_SELECTED = {};
    CURRENT_TABLE_ROWS_SELECTED = {};

    //RESET REPORT SELECTOR
	TO_LOAD_STRAINS = "";
	TO_LOAD_PROJECTS = "";

    $scope.protocol_type = {};
    $scope.protocols_of_type = [];
    $scope.protocolTypeParameters = {};

    const protocols_list = Protocol_List($http);

    $scope.loadProtocols = () => {
        $scope.getProtocolTypes();
    };

    $scope.getProtocolTypes = () => {

        protocols_list.get_protocol_types((results) => {

            $scope.protocol_types = results.protocol_types;
            let options = "";

            for(const x in results.protocol_types){
                options +="<option>"+results.protocol_types[x]+"</option>";
            }

            const protocolSelEl = $("#protocol_type_selector");
            const protocolSelLoadEl = $("#protocol_type_selector_load");

            protocolSelEl.empty();
            protocolSelLoadEl.empty();
            protocolSelEl.append(options);
            protocolSelLoadEl.append(options);

            protocolSelEl.on("change", () => {
                $scope.loadProtocolCreator($("#protocol_type_selector option:selected").text());
            });
            protocolSelLoadEl.on("change", () => {
                $scope.loadProtocolType($("#protocol_type_selector_load option:selected").text());
            });

            protocolSelEl.trigger("change");
            protocolSelLoadEl.trigger("change");

        });
    };

    $scope.addProtocol = () => {

        protocols_list.add_protocol( (results) => {
        });

    };

    $scope.loadProtocolCreator = (selectedType) => {

        $("#new_protocol_form").css({"display":"none"});

        protocols_list.load_protocol_form(selectedType, (results) => {
            $(".to_empty").val("");
            $('.to_empty option').remove();

            $scope.protocol_parameters = results.protocol_parameters;
            $scope.protocol_type = results.protocol_type;
            $("#create_protocol_button").css({"display":"block"});

            setTimeout( () => {
                if($.inArray("used Software", results.protocol_parameters)){
                    let options = "";
                    let options_nextflow = "";
                    /*for(const x in usedSoftware){
                        options += "<option>"+usedSoftware[x]+"</option>";
                    }*/
                    for(const y in nextflow_tags){
                        options_nextflow += "<option>"+nextflow_tags[y]+"</option>";
                    }

                    const selectPickerEl = $(".selectpicker");

                    $('#select_software').empty().append(options);
                    $('#nextflow_tag').empty().append(options_nextflow);
                    $('#selectpickerparams').empty().append(options_nextflow);

                    selectPickerEl.selectpicker({});
                    selectPickerEl.selectpicker("refresh");

                    $("#new_protocol_form").css({"display":"block"});

                    $('#waiting_spinner').css({display:'none'});
                    $('#protocol_controller_div').css({display:'block'});
                }
            }, 800);
        });
    };

    $scope.loadProtocolType = (selectedType) => {

        protocols_list.get_protocols_of_type(selectedType, (results) => {

            $scope.property_fields = results.property_fields;

            let options = "";
            for(const x in results.protocols_of_type){
                options +="<option>"+results.protocols_of_type[x]+"</option>";
            }

            const protocolSelLoadEl = $("#protocol_selector_load");

            protocolSelLoadEl.empty();
            protocolSelLoadEl.append(options);
            $(".selectpicker").selectpicker("refresh");


            protocolSelLoadEl.on("change", () => {
                protocols_list.load_protocol($("#protocol_selector_load" +
                    " option:selected").text(), (results) => {
                    $scope.$apply( () => {
                        $scope.selected_protocol = results.protocol;
                    })
                    $("#div_protocol_show").css({display:"block"});

                    $(".selectpicker").selectpicker("refresh");

                });
            });

            setTimeout(() => {
                protocolSelLoadEl.trigger("change");
            },300);

        });
    };

    $scope.loadProtocol = (selectedProtocol) => {

        const protocolEl = $("#div_protocol_show");

        protocolEl.css({display:"none"});

        protocols_list.load_protocol(selectedProtocol, (results) => {
            $scope.selected_protocol = results.protocol;
            protocolEl.css({display:"block"});
        });
    };

    $scope.getProtocolFields = (uri) => {

        protocols_list.get_protocol_fields(uri, (results) => {
            $scope.property_fields = results.property_fields.reverse();
        });
    };

    $scope.checkProtocolParameters = () => {
        const selected_text = $("#selectpickerparams option:selected").text();
        protocols_list.check_protocol_parameters(selected_text, (results) => {

            $("#parametersContent").html("<pre>"+String(results.data.content)+"</pre>");
            console.log(results);
        });
        console.log(selected_text);
    };

    $scope.removeSelectedParameter = () => {

        const selected_text = $("#parameter_select option:selected").text();
        const parameterSelEl = $('#parameter_select');
        let new_options = "";

        protocols_list.get_current_protocol_type( (results) => {

            const currentProtocolType = results.currentProtocolType;
            const new_protocolParameters = [];

            for(const x in $scope.protocolTypeParameters[currentProtocolType]){

                let to_check = $scope.protocolTypeParameters[currentProtocolType][x][0].value+":"+$scope.protocolTypeParameters[currentProtocolType][x][1].value;

                if(to_check !== selected_text){
                    new_options += "<option>"+to_check+"</option>";
                    new_protocolParameters.push($scope.protocolTypeParameters[currentProtocolType][x]);
                }
            }

            $scope.protocolTypeParameters[currentProtocolType] = new_protocolParameters;

            parameterSelEl.empty();
            parameterSelEl.append(new_options);
            $(".selectpicker").selectpicker("refresh");
        });

    };

    $scope.AddParameters = () => {

        const parameterEl = $('#parameter_select');

        protocols_list.get_current_protocol_type( (results) => {
            const parameterObject = $('#new_data_form').serializeArray();
            const currentProtocolType = results.currentProtocolType;

            if (!$scope.protocolTypeParameters.hasOwnProperty(currentProtocolType)){
                $scope.protocolTypeParameters[currentProtocolType] = [];
            }

            $scope.protocolTypeParameters[currentProtocolType].push(parameterObject);
            $scope.protocol_parameters = $scope.protocolTypeParameters[currentProtocolType];

            let option = "";

            for(const x in $scope.protocolTypeParameters[currentProtocolType]){
                option += "<option>"+$scope.protocolTypeParameters[currentProtocolType][x][0].value+":"+$scope.protocolTypeParameters[currentProtocolType][x][1].value+"</option>";
            }

            parameterEl.empty();
            parameterEl.append(option);

            $('.entered_params').val("");
            $(".selectpicker").selectpicker("refresh");

        });

    };

});