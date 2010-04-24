require 'sinatra'
require 'flickraw'
require 'haml'
require 'yaml'

# Some basic information about an image (on Flickr)
class Image
  attr_accessor :id, :img_url, :flickr_url, :title, :date
  
  # figure out flickr image url
  def get_img_url(photo)
    unless photo.respond_to?(:url_l)
      FlickRaw::url(photo)
    else
      photo.url_l
    end
  end
  
  def initialize(photo, url=nil)
    @id, @title, @date = photo.id, photo.title
    if url.nil?
      @date = photo.datetaken[0..9]
      @img_url = get_img_url(photo)
    else
      @date = photo.dates.taken[0..9]
      @img_url = url
    end
    @flickr_url = FlickRaw.url_photopage(photo)
  end
end

# basic information about a set
class FlickrSet
  attr_accessor :id, :title, :thumbnail, :slug
  
  def slug
    @slug ||= @title.downcase.gsub(/[^a-z0-9_]/, '-')
  end
  
  def initialize(id, title, thumbnail, slug = nil)
    @id, @title, @thumbnail, @slug = id, title, thumbnail, slug
  end
end

class Configure
  attr_accessor :conf, :sets
  
  def initialize
    # load up conf file
    @conf = YAML::load_file(File.dirname(__FILE__) + '/conf.yml')
    @conf[:user_id] = flickr.people.findByUsername(:username => @conf[:user]).id
    user = flickr.people.getInfo(:user_id => @conf[:user_id])
    @conf[:flickr_profile] = user.profileurl
    @conf[:name] = user.realname

    # read sets file
    @sets = YAML::load_file(File.dirname(__FILE__) + '/sets.yml')
  end
end

# Sinatra !!

configure do
  # use HTML5 when generating HTML
  set :haml, :format => :html5, :attr_wrapper  => '"'
   
  CONFIG = Configure.new
end

before do
  @config = CONFIG
end

helpers do
  # Loads 10 images from Flickr, offset by however many pages.
  # If :tag is specified in the conf file, we filter by that
  # machine tag. if tag is supplied as a parameter, we will
  # filter by that instead.
  def load_images(page, tag=nil)
    @page = page.to_i
    @tag = tag
    params = { :user_id => @config.conf[:user_id], :extras => 'date_taken, url_l, path_alias' }
    params[:machine_tags] = @config.conf[:tag] unless @config.conf[:tag].nil?
    params[:machine_tags] = tag unless tag.nil?
    params[:per_page] = 10 unless page == 0
    params[:page] = page unless page == 0
    photos = flickr.photos.search(params)
    @pages = photos.pages
    @sequence = build_sequence(photos)
  end

  # load all the photos in the given flickr set.
  def load_set(id)
    @page = 0
    @tag = id
    params = { :user_id => @config.conf[:user_id], :extras => 'date_taken, url_l, path_alias', :photoset_id => id }
    set_info = flickr.photosets.getPhotos(params)
    @sequence = build_sequence(set_info.photo)
  end

  # build list of images.
  def build_sequence(photos)
    return [] if photos.nil?
    photos.map { |photo| Image.new(photo) }
  end
  
  def prev_link
    case
    when @page <= 1
      "Prev"
    when @page == 2
      "<a href=\"/\" class=\"prev_page\">Prev</a>"
    else
      "<a href=\"/page/#{@page - 1}\" class=\"prev_page\">Prev</a>"
    end
  end
  
  def next_link
    @page >= @pages ? "Next" : "<a href=\"/page/#{@page + 1}\" class=\"next_page\">Next</a>"
  end
end

# loads the most recent photos from Flickr
get '/' do
  load_images(1)
  @show_nav = true
  haml :index
end

# loads the most recent photos from Flickr, offset by however many pages.
get '/page/:num' do |page|
  load_images(page)
  @show_nav = true
  haml :index
end

# get list of sets visibile at vqvz.
get '/sets' do
  @sets = @config.sets.map do |slug, set|
    FlickrSet.new(set[:set_id], set[:title], set[:thumbnail], slug)
  end
  haml :sets
end

# load set using Flickr set ID
get %r{/set/(\d+)} do |id|
  load_set(id)
  haml :index
end

# load machine tag or local set name
get '/set/:name' do |name|
  @config.sets[name].nil? ? load_images(0, "vqvz:set=#{name}") : load_set(@config.sets[name][:set_id])
  haml :index
end

# load a single image from Flickr
get %r{/photo/(\d+)} do |id|
  info = flickr.photos.getInfo(:photo_id => id)
  sizes = flickr.photos.getSizes(:photo_id => id)
  img_url = sizes.find {|s| s.label == 'Large' }
  img_url ||= sizes.find {|s| s.label == 'Medium' } # always exists
  @photo = Image.new(info, img_url.source)
  haml :photo
end

get '/:name' do |@name|
  halt 404 unless File.exists?(File.dirname(__FILE__) + "/views/_#{@name}.haml")
  haml :simple
end

# Error Handlers in Production

not_found do
  @name = 'WTF'
  haml :simple
end

error do
  @name = 'WTF'
  haml :simple
end
