<!DOCTYPE HTML>
<html>
    <head>
        <title>HTC MusicBot Queue</title>
        <link type="text/css" href="../main.css" rel="stylesheet">
        <meta name=viewport content="width=device-width, initial-scale=1">
    </head>
    <body>
        <div id="header">HTC MusicBot Queue</div>

        <div id="container">
        </div>

    <script src="https://code.jquery.com/jquery-3.2.1.min.js" type="text/javascript"></script>
    <script type="text/javascript">
    var key = '{{key}}';
    var interval = 5000;

    var entityMap = {
      '&': '&amp;',
      '<': '&lt;',
      '>': '&gt;',
      '"': '&quot;',
      "'": '&#39;',
      '/': '&#x2F;',
      '`': '&#x60;',
      '=': '&#x3D;'
    };

    function escapeHtml(string) {
      return String(string).replace(/[&<>"'`=\/]/g, function (s) {
        return entityMap[s];
      });
    }

    function loop() {
        console.log('loop');
        $.post("queue", {
                'key': key,
                'resource': 'FULL_QUEUE'
            },
            function (data, textStatus) {
                console.log(data);
                console.log(textStatus);

                var response = jQuery.parseJSON(data);

                if (response['code'] === 1000) {
                    $('#container').html('')
                    for (var i=0; i<response['d']['queue_length']; i++) {
                        $('#container').append(
                            '<div id="card"><b>' +
                            escapeHtml(response['d']['queue'][i][0]) +
                            '</b> Queued by <b>' +
                            escapeHtml(response['d']['queue'][i][1]) +
                            '</b></div>'
                        )
                    }
                }

                setTimeout(loop, interval);
            }
        ).fail(function(response) {
            setTimeout(loop, interval);
        });
    }

    $(loop);
    </script>

    </body>
</html>
