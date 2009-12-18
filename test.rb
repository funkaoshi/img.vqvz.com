require 'rubygems'
require 'flickraw'

photos = flickr.photos.search :machine_tags => 'funkaoshi:ext=', :extras => 'date_taken, url_m'
photos.each do |photo|
    r = flickr.photos.getInfo :photo_id => photo.id, :secret => photo.secret
      puts "#{FlickRaw.url_b(r)}"
    end
    
