
var colors = d3.scale.category20b();
var width = 500, height = 350;

var svg_a = d3.select("#cloud_a").append('svg')
        .attr('width', width)
        .attr('height', height)
        .append('g')
        .attr('transform', "translate(" + [width >> 1, height >> 1] + ")");

var svg_b = d3.select("#cloud_b").append('svg')
    .attr('width', width)
    .attr('height', height)
    .append('g')
    .attr('transform', "translate(" + [width >> 1, height >> 1] + ")");


var calculateCloud = function(wordCount, type) {

    var function_draw;

    if(type == "A") {
        function_draw = drawCloud_a;
    }
    else {
        function_draw = drawCloud_b;
    }

    var words_array = [];

    var typeFace = 'Impact';
	var width = 500, height = 350;

    var fontSize = d3.scale.linear()
             .domain([0, d3.max(wordCount, function(d) { return d.size} )])
                .range([15, 40]);

    var cloud = d3.layout.cloud()
        .size([width, height])
        .words(wordCount)
        .rotate(function() { return ~~(Math.random()*2) * 90;}) // 0 or 90deg
        .font(typeFace)
        .fontSize(function(d) { return fontSize(d.size) })
        .on('end', function_draw);
        
    return cloud;
};


var set_vis = function(vis) {
    vis.enter().append('text')

        .style('font-size', function(d) {
            return d.size + 'px';
        })
        .style('font-family', function(d) {
            return d.font;
        })
        .style('fill', function(d, i) {
            return colors(i);
        })
        .attr('text-anchor', 'middle')
        .attr('transform', function(d) {
          return 'translate(' + [d.x, d.y] + ')rotate(' + d.rotate + ')';
        })
        .text(function(d) { return d.text; });
}

var drawCloud_a = function(words) {
    var vis = svg_a.selectAll('text').data(words);
    set_vis(vis);
};

var drawCloud_b = function(words) {
    var vis = svg_b.selectAll('text').data(words);
    set_vis(vis);
};

var information_a = function(result) {

    document.getElementById("image_a").innerHTML = "<img src='" + result['user_a']['photo'] + "' class='img-thumbnail rounded float-right'>";
    document.getElementById("name_a").innerHTML = "<h2 class='card-title'>" + result['user_a']['name'] + "</h2>";
    document.getElementById("description_a").innerHTML = "<p class='card-text small'>" + result['user_a']['description'] + "</p>";

    hashtag_htm = "";


    for(hashtag in result['user_a']['hashtags']) {
        
        hashtag_htm += "<span class='badge badge-danger'>" + result['user_a']['hashtags'][hashtag][0] + "</span> ";
    }

    document.getElementById("hashtag_a").innerHTML = hashtag_htm;

    
    top_terms_html = "<ul class='list-group'>";
    top_terms_html = "<ul class='list-group'>";
    top_terms_html += "<li class='list-group-item active' style='background-color: #19334d; color: #ffffff; '>";
    top_terms_html += "Termos relevantes"; 
    top_terms_html += "<div><small>Quantidade de vezes que os termos aparecem nas postagens.</small></div>";
    top_terms_html += "</li>";


    for(word in result['topics_name']) {

        var name = result['topics_name'][word]
        var quant = result['user_a']['topics'][name]

        if(quant == null) {
            quant = 0;
        }

        top_terms_html += "<li class='list-group-item d-flex justify-content-between align-items-center'>";
        top_terms_html += name;
        top_terms_html += "<span class='badge badge-dark badge-pill'>" + quant + "</span>";
        top_terms_html += "</li>";
    }

    top_terms_html += "</ul>"

    document.getElementById("terms_list_a").innerHTML = top_terms_html
    


};

var information_b = function(result) {

    document.getElementById("image_b").innerHTML = "<img src='" + result['user_b']['photo'] + "' class='img-thumbnail rounded float-right'>";
    document.getElementById("name_b").innerHTML = "<h2 class='card-title'>" + result['user_b']['name'] + "</h2>";
    document.getElementById("description_b").innerHTML = "<p class='card-text small'>" + result['user_b']['description'] + "</p>";

    hashtag_htm = "";


    for(hashtag in result['user_b']['hashtags']) {
        
        hashtag_htm += "<span class='badge badge-primary'>" + result['user_b']['hashtags'][hashtag][0] + "</span> ";
    }

    document.getElementById("hashtag_b").innerHTML = hashtag_htm;

    top_terms_html = "<ul class='list-group'>";
    top_terms_html += "<li class='list-group-item active' style='background-color: #19334d; color: #ffffff; '>";
    top_terms_html += "Termos relevantes"; 
    top_terms_html += "<div><small>Quantidade de vezes que os termos aparecem nas postagens.</small></div>";
    top_terms_html += "</li>";


    for(word in result['topics_name']) {

        var name = result['topics_name'][word]
        var quant = result['user_b']['topics'][name]

        if(quant == null) {
            quant = 0;
        }

        top_terms_html += "<li class='list-group-item d-flex justify-content-between align-items-center'>";
        top_terms_html += name;
        top_terms_html += "<span class='badge badge-dark badge-pill'>" + quant + "</span>";
        top_terms_html += "</li>";
    }

    top_terms_html += "</ul>"

    document.getElementById("terms_list_b").innerHTML = top_terms_html

};

var getProfile = function () {

    document.getElementById("profile_information").style="display:none";
    document.getElementById("msg").innerHTML = "<div class='alert alert-warning'>Carregando informações do perfil. Aguarde ... </div>";

    $.ajax({
        url: '/profile_information', // Url do lado server que vai receber o arquivo
        processData: false,
        contentType: false,
        type: 'POST',
        success: function (result) {

            document.getElementById("profile_information").style="display:";
            document.getElementById("msg").innerHTML = "";

            information_a(result);
            information_b(result);


            var words_a = result['user_a']['words'];
            var words_array_a = [];


            var words_b = result['user_b']['words'];
            var words_array_b = []

            for (key in words_a){
				words_array_a.push({text: key, size: words_a[key]})
            }

            for (key in words_b){
				words_array_b.push({text: key, size: words_b[key]})
            }
            
            cloud_a = calculateCloud(words_array_a, "A");
            cloud_b = calculateCloud(words_array_b, "B");
            
            cloud_a.start();
            cloud_b.start();

            

        },
        error: function (result) {
            document.getElementById("profile_information").style="display:none";
            document.getElementById("msg").innerHTML = "<div class='alert alert-danger'>Ocorreu um erro ao processar o perfil. Tente novamente mais tarde. Clique <a href='/'>aqui</a> para voltar.</div>";
            
        }
    });

}


getProfile();