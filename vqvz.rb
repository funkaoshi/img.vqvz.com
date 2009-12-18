require 'sinatra'
require 'erubis'
require 'flickraw/lib/flickraw.rb'

configure do
  CONF = YAML::load_file("conf.yml")
  CONF[:user_id] = flickr.people.findByUsername(:username => CONF[:user]).id
  user = flickr.people.getInfo(:user_id => CONF[:user_id])
  CONF[:total_pages] = user.photos.count.to_i / 10 + 1
  CONF[:flickr_profile] = user.profileurl
  CONF[:name] = user.realname
end

before do
  @config = CONF
end

# Some basic information about an image (on Flickr)
class Image
  attr_accessor :id, :img_url, :flickr_url, :title, :date
  def initialize(id, img_url,title, date)
    @id = id
    @img_url = img_url
    @flickr_url = "http://flickr.com/photos/#{CONF[:user]}/#{id}"
    @title = title
    @date = date
  end
end

helpers do
  # Loads 10 images from Flickr, offset by however many pages.
  # If :tag is specified in the conf file, we filter by that
  # machine tag.
  def load_images(page)
    @page = page.to_i
    params = { :per_page => 10, :page => page, :user_id => CONF[:user_id], :extras => 'date_taken' }
    params[:machine_tags] = CONF[:tag] unless CONF[:tag].nil?
    photos = flickr.photos.search(params)
    @sequence = photos.map do |photo| 
      sizes = flickr.photos.getSizes(:photo_id => photo.id)
      size = sizes.find { |s| s.label == 'Large' }
      size ||= sizes.find { |s| s.label == 'Medium'}
      Image.new(photo.id, size.source, photo.title, photo.datetaken[0..9])
    end
  end
end
    
# loads the most recent photos from Flickr
get '/' do
  load_images(1)
  erb :index
end

# loads the most recent photos from Flickr, offset by however many pages.
get '/:num' do |page|
  load_images(page)
  erb :index
end

get '/about/?' do 
  erb :about
end

error do
  'Sorry there was a nasty error - ' + request.env['sinatra.error'].name
end