var {google} = require('googleapis');
var Twit = require('twit');
var request = require('request');
var emojiRegex = require('emoji-regex');
var AWS = require('aws-sdk');

// youtube api
var youtube = google.youtube({
    version: 'v3',
    auth: process.env.YOUTUBE_API_KEY
});

// twitter api
var twitter = new Twit({
    consumer_key:         process.env.CONSUMER_KEY,
    consumer_secret:      process.env.CONSUMER_SECRET,
    access_token:         process.env.ACCESS_TOKEN,
    access_token_secret:  process.env.ACCESS_TOKEN_SECRET,
    timeout_ms:           60*1000,  // optional HTTP request timeout to apply to all requests.
    strictSSL:            true,     // optional - requires SSL certificates to be valid.
});

var getParams = {
    TableName: 'DumbGenie',
    Key: {
      'Type' : {S: 'TweetId'}
    }
};

// dynamo database
AWS.config.update({region: 'us-west-2'});
var ddb = new AWS.DynamoDB({apiVersion: '2012-08-10'});

const REGEX_START = /^i wish i knew how to .*/i;
const REGEX_END = /[^.,?!;:#/]*/;
const REGEX_ACRONYM = /(?<=\s)(lol|omf?g|lmf?ao+|smf?h)(?=\s|$|[.,;:?!#/])/ig;
const REGEX_EMOJI = emojiRegex();
const PREFIX_LENGTH = 14;
const YOUTUBE_URL = 'https://www.youtube.com/watch?v=';

// lambda function enters here
exports.handler = event => {
    getTweetId();
}

// get tweet id of last tweet responded to
function getTweetId() {
    ddb.getItem(getParams, function(err, data) {
        if (err) {
            console.error("Error", err);
        } else {
            searchTweets(data.Item.TweetId.S);
        }
    });
}

// search for all tweets since the last tweet responded to
function searchTweets(tweetId) {
    twitter.get('search/tweets', {q: '"I wish I knew how to"', count: 50, result_type: 'recent', lang: 'en', since_id: tweetId}, (err, data, response) => {
        putTweetId(data.statuses[0].id_str)
        data.statuses.forEach(status => {
            var text = status.text.match(REGEX_START);
            if (text === null || status.entities.urls.length !== 0) return;
            cleanText = text[0].replace(REGEX_EMOJI, '.').replace(REGEX_ACRONYM, '.');
            addPunctuation(cleanText, status.id_str);
        });
    });
}

// update tweet id
function putTweetId(id) {
    var putParams = {
        TableName: 'DumbGenie',
        Item: {
            'Type' : {S: 'TweetId'},
            'TweetId' : {S: id}
        }
    };

    ddb.putItem(putParams, function(err, data) {
        if (err) {
            console.log("Error", err);
        }
    });
}

// add punctuation to tweet
function addPunctuation(text, id) {
    var data = 'text=' + text;
    var options = {
        url: 'http://bark.phon.ioc.ee/punctuator',
        body: data,
        headers: {'content-type' : 'application/x-www-form-urlencoded'}
    };

    request.post(options, (err, response, body) => {
        if (err) return console.error(err);
        if (response.statusCode == 200) {
            return searchVideo(body.match(REGEX_END)[0].substring(PREFIX_LENGTH).trim(), id);
        }
    });
}

// search youtube for most relevant video
function searchVideo(data, id) {
    youtube.search.list({part: 'snippet', q: data, maxResults: 1, order: 'relevance', type: 'video'}).then(response => {
        if (response.data.items.length <= 0) return;
        var url = YOUTUBE_URL + response.data.items[0].id.videoId;
        tweetReply(url, id, data);
    }, err => {
        console.error(err);
    });
}

// tweet a reply to the original tweet
function tweetReply(url, id, data) {
    var reply = 'Wish granted! ' + data + ': ' + url;
    twitter.post('statuses/update', {status: reply, in_reply_to_status_id: id, auto_populate_reply_metadata: 'true'}, (err, data, response) => {
        if (err) return console.error(err);
        console.log('{"Reply": "' + reply + '", "ID: "' + id + '"}');
    });
}
